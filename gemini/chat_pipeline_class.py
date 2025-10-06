from google.genai import types
from google import genai
import json
import os
from dotenv import load_dotenv
import snowflake.connector
import logging
import traceback
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add gmaps directory to path for busyness imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from gmaps.busyness_helper import get_busyness_at_time, find_peak_time, extract_busyness_query_type
    BUSYNESS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Busyness module not available: {e}")
    BUSYNESS_AVAILABLE = False


def convert_to_serializable(obj):
    """Convert non-JSON serializable objects to strings"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj


def process_query_results(data):
    """Convert query results to JSON-serializable format"""
    processed = []
    for row in data:
        processed_row = tuple(convert_to_serializable(item) for item in row)
        processed.append(processed_row)
    return processed


class ChatSession:
    """
    Maintains a persistent Gemini chat session with automatic context retention.
    This is much more efficient than replaying history on each message.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize a new chat session with database integration.
        
        Args:
            api_key: Gemini API key
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.message_count = 0
        self.conversation_history = []
        
        logger.info("🎬 Initializing ChatSession with database integration")
    
    def send_message(self, message: str, personal_context: str = "", voice_mode: bool = False) -> str:
        """
        Send a message with full pipeline: intent classification → database query → response.
        Maintains conversation history for context.
        
        Args:
            message: User message
            personal_context: Optional personal context string
            voice_mode: Whether this is a voice conversation (uses different tone)
            
        Returns:
            str: Assistant's response with database data
        """
        try:
            self.message_count += 1
            logger.info("="*70)
            logger.info(f"💬 ChatSession Message #{self.message_count}: {message}")
            if personal_context:
                logger.info(f"👤 Personal context provided ({len(personal_context)} chars)")
            if self.conversation_history:
                logger.info(f"📚 Conversation history: {len(self.conversation_history)} messages")
            logger.info("="*70)
            
            # Use the full pipeline with conversation history
            response = send_user_message(self.api_key, message, personal_context, voice_mode, self.conversation_history)
            
            # Store in conversation history
            self.conversation_history.append({
                'role': 'user',
                'content': message
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            logger.info(f"✅ ChatSession - Response generated ({len(response)} chars)")
            logger.info("="*70)
            return response
            
        except Exception as e:
            # Log the error and re-raise with more context
            error_msg = f"Pipeline error at message {self.message_count}: {str(e)}"
            logger.error(f"❌ ERROR: {error_msg}")
            logger.error(traceback.format_exc())
            raise Exception(error_msg) from e
    
    def send_message_stream(self, message: str, personal_context: str = "", voice_mode: bool = False):
        """
        Send a message with streaming response. Maintains conversation history.
        
        Args:
            message: User message
            personal_context: Optional personal context string
            voice_mode: Whether this is a voice conversation
            
        Yields:
            str: Chunks of the assistant's response
        """
        try:
            self.message_count += 1
            logger.info("="*70)
            logger.info(f"🌊 ChatSession STREAMING Message #{self.message_count}: {message}")
            if personal_context:
                logger.info(f"👤 Personal context provided ({len(personal_context)} chars)")
            if self.conversation_history:
                logger.info(f"📚 Conversation history: {len(self.conversation_history)} messages")
            logger.info("="*70)
            
            # Get history BEFORE adding current message (so it doesn't include itself)
            history_for_context = list(self.conversation_history)
            
            # Store user message immediately
            self.conversation_history.append({
                'role': 'user',
                'content': message
            })
            
            # Stream the response with conversation history
            full_response = ""
            for chunk in send_user_message_stream(self.api_key, message, personal_context, voice_mode, history_for_context):
                full_response += chunk
                yield chunk
            
            # Store complete assistant response in history
            self.conversation_history.append({
                'role': 'assistant',
                'content': full_response
            })
            
            logger.info(f"✅ ChatSession - Streaming complete ({len(full_response)} chars)")
            logger.info("="*70)
            
        except Exception as e:
            error_msg = f"Pipeline streaming error at message {self.message_count}: {str(e)}"
            logger.error(f"❌ ERROR: {error_msg}")
            logger.error(traceback.format_exc())
            raise Exception(error_msg) from e
    
    def get_message_count(self) -> int:
        """Get the number of messages sent in this session."""
        return self.message_count


def extract_query_filters(user_message):
    """
    Extract specific filters from user message for targeted querying.
    Returns dict with location, meal_period, day filters.
    """
    import re
    
    filters = {}
    message_lower = user_message.lower()
    
    # Extract dining hall location
    location_map = {
        'busch': 'Busch Dining Hall',
        'livingston': 'Livingston Dining Commons',
        'neilson': 'Neilson Dining Hall',
        'atrium': 'The Atrium'
    }
    for key, value in location_map.items():
        if key in message_lower:
            filters['location'] = value
            break
    
    # Extract meal period
    if 'breakfast' in message_lower:
        filters['meal_period'] = 'Breakfast'
    elif 'lunch' in message_lower:
        filters['meal_period'] = 'Lunch'
    elif 'dinner' in message_lower:
        filters['meal_period'] = 'Dinner'
    
    # Extract day of week
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for day in days:
        if day in message_lower:
            filters['day_of_week'] = day.capitalize()
            break
    
    # Check for "today" or "tomorrow"
    if 'today' in message_lower:
        filters['relative_day'] = 'today'
    elif 'tomorrow' in message_lower:
        filters['relative_day'] = 'tomorrow'
    
    logger.info(f"🔍 Extracted filters from query: {filters}")
    return filters


def query_snowflake(intent_data, user_message=None):
    """
    Query Snowflake database based on intent classification.
    
    Args:
        intent_data: JSON object with category information from intent classification
    
    Returns:
        dict: Query results or error message
    """
    try:
        # Parse the category from intent
        category = intent_data.get('category', '')
        logger.info(f"🔍 SNOWFLAKE QUERY - Intent data received: {intent_data}")
        
        # Connect to Snowflake
        logger.info("📡 Connecting to Snowflake...")
        conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE'),
            schema=os.getenv('SNOWFLAKE_SCHEMA')
        )
        logger.info("✅ Snowflake connection established")
        
        cursor = conn.cursor()
        results = {}
        
        # Parse category - handle both string and list formats
        categories = []
        if isinstance(category, list):
            categories = category
        elif isinstance(category, str):
            categories = [category]
        
        logger.info(f"📋 Categories to query: {categories}")
        
        # Extract filters from user message for smart querying
        filters = extract_query_filters(user_message) if user_message else {}
        
        # Query based on categories
        for cat in categories:
            logger.info(f"🔎 Processing category: {cat}")
            if "Dining Menu" in cat:
                logger.info("🍽️  Querying DINING_HALL_MENUS table...")
                
                # Build dynamic WHERE clause based on filters
                where_clauses = ["DATE >= CURRENT_DATE() - 1"]
                
                if filters.get('location'):
                    where_clauses.append(f"LOCATION = '{filters['location']}'")
                    logger.info(f"🎯 Filtering by location: {filters['location']}")
                
                if filters.get('meal_period'):
                    where_clauses.append(f"MEAL_PERIOD = '{filters['meal_period']}'")
                    logger.info(f"🎯 Filtering by meal period: {filters['meal_period']}")
                
                if filters.get('day_of_week'):
                    where_clauses.append(f"DAY_OF_WEEK = '{filters['day_of_week']}'")
                    logger.info(f"🎯 Filtering by day: {filters['day_of_week']}")
                
                where_clause = " AND ".join(where_clauses)
                
                # Determine limit based on specificity
                limit = 100 if filters else 300  # Fewer results if filtered
                
                query = f"""
                    SELECT LOCATION, CAMPUS, DATE, DAY_OF_WEEK, MEAL_PERIOD, CATEGORY, ITEM
                    FROM DINING_HALL_MENUS
                    WHERE {where_clause}
                    ORDER BY DATE, 
                             CASE MEAL_PERIOD 
                                 WHEN 'Breakfast' THEN 1 
                                 WHEN 'Lunch' THEN 2 
                                 WHEN 'Dinner' THEN 3 
                             END,
                             LOCATION
                    LIMIT {limit}
                """
                
                logger.info(f"📝 Executing query with filters: {filters}")
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                # Convert dates to strings for JSON serialization
                processed_data = process_query_results(data)
                results['dining_menus'] = {
                    'columns': columns,
                    'data': processed_data
                }
                logger.info(f"✅ Retrieved {len(data)} dining menu items")
                if processed_data:
                    logger.info(f"📝 Sample: {processed_data[0]}")
                    # Log meal period distribution
                    meal_periods = {}
                    for row in processed_data:
                        meal_period = row[4] if len(row) > 4 else 'Unknown'
                        meal_periods[meal_period] = meal_periods.get(meal_period, 0) + 1
                    logger.info(f"📊 Meal period distribution: {meal_periods}")
            
            if "Dining Hours" in cat:
                logger.info("⏰ Querying RETAIL_FOOD_LOCATIONS table...")
                cursor.execute("SELECT * FROM RETAIL_FOOD_LOCATIONS")
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                processed_data = process_query_results(data)
                results['dining_hours'] = {
                    'columns': columns,
                    'data': processed_data
                }
                logger.info(f"✅ Retrieved {len(data)} dining locations with hours")
            
            if "Gym Hours" in cat:
                logger.info("🏋️  Querying GYM_HOURS table...")
                cursor.execute("SELECT * FROM GYM_HOURS ORDER BY GYM_NAME, DAY")
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                processed_data = process_query_results(data)
                results['gym_hours'] = {
                    'columns': columns,
                    'data': processed_data
                }
                logger.info(f"✅ Retrieved {len(data)} gym hour entries")
            
            if "Campus Events" in cat:
                logger.info("🎉 Querying CAMPUS_EVENTS table...")
                cursor.execute("SELECT * FROM CAMPUS_EVENTS ORDER BY DATE_TIME LIMIT 50")
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                processed_data = process_query_results(data)
                results['campus_events'] = {
                    'columns': columns,
                    'data': processed_data
                }
                logger.info(f"✅ Retrieved {len(data)} campus events")
            
            if "Library Hours" in cat:
                logger.info("📚 Querying LIBRARY_HOURS table...")
                cursor.execute("SELECT * FROM LIBRARY_HOURS")
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                processed_data = process_query_results(data)
                results['library_hours'] = {
                    'columns': columns,
                    'data': processed_data
                }
                logger.info(f"✅ Retrieved {len(data)} library hour schedules")
            
            if "Library Locations" in cat:
                logger.info("📍 Querying LIBRARY_LOCATIONS table...")
                cursor.execute("SELECT * FROM LIBRARY_LOCATIONS")
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                processed_data = process_query_results(data)
                results['library_locations'] = {
                    'columns': columns,
                    'data': processed_data
                }
                logger.info(f"✅ Retrieved {len(data)} library locations")
        
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "data": results
        }
        
    except Exception as e:
        print(f"Snowflake query error: {str(e)}")
        return {
            "status": "error",
            "message": f"Database error: {str(e)}",
            "data": None
        }


def query_busyness(user_message):
    """
    Query location busyness based on user message.
    Automatically determines if it's a specific time or peak time query.
    
    Args:
        user_message: User's query text
    
    Returns:
        dict: Busyness query results
    """
    if not BUSYNESS_AVAILABLE:
        return {
            "status": "unavailable",
            "message": "Busyness data is currently unavailable"
        }
    
    try:
        query_type = extract_busyness_query_type(user_message)
        logger.info(f"🔍 Busyness query type: {query_type}")
        
        if query_type == "peak_time":
            logger.info("📊 Finding peak busy times...")
            result = find_peak_time(user_message)
        else:
            logger.info("⏰ Checking busyness at specific time...")
            result = get_busyness_at_time(user_message)
        
        return {
            "status": result.get("status", "success"),
            "data": result,
            "query_type": query_type
        }
    
    except Exception as e:
        logger.error(f"❌ Busyness query error: {e}")
        return {
            "status": "error",
            "message": f"Error checking busyness: {str(e)}"
        }


def assemble_final_context(user_message, intent_response, sql_response, personal_context="", busyness_response=None, conversation_history=None):
    """
    Assembles the final context prompt for the thinking model.
    
    Args:
        user_message: Original user question
        intent_response: Response from intent classification model
        sql_response: Response from SQL query (or None if not applicable)
        personal_context: Optional personal context string
        busyness_response: Response from busyness query (or None if not applicable)
        conversation_history: List of previous messages
    
    Returns:
        str: Assembled context for the thinking model
    """
    context_parts = []
    
    # Add conversation history if available
    if conversation_history and len(conversation_history) > 0:
        context_parts.append("=== CONVERSATION HISTORY ===")
        # Include last 10 messages for context (5 exchanges)
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        for msg in recent_history:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            context_parts.append(f"{role_label}: {msg['content']}")
        context_parts.append("=== END CONVERSATION HISTORY ===\n")
    
    # Add personal context if available
    if personal_context:
        context_parts.append("=== PERSONAL CONTEXT ===")
        context_parts.append(personal_context)
        context_parts.append("\n=== END PERSONAL CONTEXT ===\n")
    
    context_parts.append(f"Current User Question: {user_message}")
    context_parts.append(f"\nIdentified Intent/Categories: {intent_response}")
    
    if sql_response and sql_response.get("status") == "success":
        context_parts.append(f"\nDatabase Results:\n{json.dumps(sql_response['data'], indent=2)}")
    elif sql_response and sql_response.get("status") == "not_implemented":
        context_parts.append(f"\nNote: {sql_response['message']}")
    
    if busyness_response and busyness_response.get("status") in ["success", "unavailable"]:
        context_parts.append(f"\nBusyness Data:\n{json.dumps(busyness_response.get('data', {}), indent=2, default=str)}")
    
    return "\n".join(context_parts)


def get_thinking_model_response(api_key, user_message, context, voice_mode=False):
    """
    Sends assembled context to Gemini Pro (thinking model) for final response.
    
    Args:
        api_key: Gemini API key
        user_message: Original user message
        context: Assembled context from previous steps
        voice_mode: Whether this is a voice conversation
    
    Returns:
        str: Final response from thinking model
    """
    
    # Voice-specific system prompt for more natural conversation
    voice_system_prompt = """
    You are a friendly, energetic Rutgers University assistant having a VOICE CONVERSATION.
    
    You have access to real-time information about:
    - Dining menus and hours
    - Gym schedules
    - Campus events
    - Location busyness/crowdedness
    - General Rutgers info
    
    VOICE CONVERSATION RULES:
    - Keep responses SHORT and CONVERSATIONAL (2-4 sentences max)
    - Sound natural like you're talking to a friend, not writing an essay
    - Use casual language: "Yeah!", "Awesome!", "Let me check that out"
    - Be enthusiastic and upbeat!
    - Skip complex formatting - just speak naturally
    - For lists, say "You've got a few options" instead of bullet points
    - Use emojis sparingly, only for emphasis
    
    BUSYNESS DATA:
    - 0-30%: "Pretty quiet" or "Not busy at all"
    - 30-60%: "Moderately busy" or "Getting some traffic"
    - 60-85%: "Pretty packed" or "Really busy"
    - 85-100%: "Super crowded" or "Absolutely packed"
    
    Remember: You're SPEAKING, not writing! Keep it medium-short, natural, and energetic! ALSO HAVE A HOT AND SENSUAL ATTRACTIVE TONE
    """
    
    # Text-specific system prompt for more detailed responses
    text_system_prompt = """
    You are a helpful Rutgers University assistant with access to information about:
    - Dining menus across campus
    - Dining hall and restaurant hours
    - Gym hours and facilities
    - Campus events
    - Location busyness/crowdedness (real-time and historical data)
    - General Rutgers information
    
    When the SQL database is not set up yet, use your knowledge to provide helpful answers 
    to general questions about Rutgers.  If the question specifically requires real-time data 
    from the database (like current menu items or specific hours), 
    DO NOT MENTION THE DATABASE IS NOT SET UP OR BEING WORKED BUT RATHER ANSWER
    THE QUESTION TO THE BEST OF YOUR ABILITY
    
    BUSYNESS DATA INTERPRETATION:
    - Popularity values are 0-100% indicating how crowded a location is
    - 0-30%: Light/Not busy 🟢
    - 30-60%: Moderately busy 🟡
    - 60-85%: Very busy 🟠
    - 85-100%: Extremely crowded 🔴
    - Source can be 'live' (real-time) or 'historical' (typical for that time)
    - When busyness data is paired with hours data, check if the location is even open at the requested time
    - If location is closed at the requested time, prioritize mentioning that over busyness data
    
    FORMATTING RULES:
    - Use ONLY plain text - NO markdown symbols (no *, **, #, ##, etc.)
    - For lists, use a simple dash and space at the start: "- Item"
    - For numbered lists, use: "1. Item", "2. Item", etc.
    - Use blank lines to separate paragraphs
    - No special formatting - just plain, clean text
    - When showing busyness, include the emoji indicators

    TONE:
    - Be concise, friendly, and helpful, casual, informal, and energetic
    - When showing busyness, include the emoji indicators
    """
    
    # Choose the appropriate system prompt
    system_prompt = voice_system_prompt if voice_mode else text_system_prompt
    
    Client = genai.Client(api_key=api_key)
    
    chat = Client.chats.create(
        model='gemini-2.0-flash',  # Faster model for quicker responses
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7
        )
    )
    
    # Combine context with user message for the thinking model
    final_prompt = f"{context}\n\nPlease provide a helpful response to the user's question."
    
    response = chat.send_message(final_prompt)
    return response.text


def get_thinking_model_response_stream(api_key, user_message, context, voice_mode=False):
    """
    Streams response from Gemini Pro (thinking model) for real-time display.
    
    Args:
        api_key: Gemini API key
        user_message: Original user message
        context: Assembled context from previous steps
        voice_mode: Whether this is a voice conversation
    
    Yields:
        str: Chunks of the response as they're generated
    """
    
    # Voice-specific system prompt for more natural conversation
    voice_system_prompt = """
    You are a friendly, energetic Rutgers University assistant having a VOICE CONVERSATION.
    
    You have access to real-time information about:
    - Dining menus and hours
    - Gym schedules
    - Campus events
    - Location busyness/crowdedness
    - General Rutgers info
    
    VOICE CONVERSATION RULES:
    - Keep responses SHORT and CONVERSATIONAL (2-4 sentences max)
    - Sound natural like you're talking to a friend, not writing an essay
    - Use casual language: "Yeah!", "Awesome!", "Let me check that out"
    - Be enthusiastic and upbeat!
    - Skip complex formatting - just speak naturally
    - For lists, say "You've got a few options" instead of bullet points
    - Use emojis sparingly, only for emphasis
    
    BUSYNESS DATA:
    - 0-30%: "Pretty quiet" or "Not busy at all"
    - 30-60%: "Moderately busy" or "Getting some traffic"
    - 60-85%: "Pretty packed" or "Really busy"
    - 85-100%: "Super crowded" or "Absolutely packed"
    
    Remember: You're SPEAKING, not writing! Keep it medium-short, natural, and energetic! ALSO HAVE A HOT AND SENSUAL ATTRACTIVE TONE
    """
    
    # Text-specific system prompt for more detailed responses
    text_system_prompt = """
    You are a helpful Rutgers University assistant with access to information about:
    - Dining menus across campus
    - Dining hall and restaurant hours
    - Gym hours and facilities
    - Campus events
    - Location busyness/crowdedness (real-time and historical data)
    - General Rutgers information
    
    When the SQL database is not set up yet, use your knowledge to provide helpful answers 
    to general questions about Rutgers.  If the question specifically requires real-time data 
    from the database (like current menu items or specific hours), 
    DO NOT MENTION THE DATABASE IS NOT SET UP OR BEING WORKED BUT RATHER ANSWER
    THE QUESTION TO THE BEST OF YOUR ABILITY
    
    BUSYNESS DATA INTERPRETATION:
    - Popularity values are 0-100% indicating how crowded a location is
    - 0-30%: Light/Not busy 🟢
    - 30-60%: Moderately busy 🟡
    - 60-85%: Very busy 🟠
    - 85-100%: Extremely crowded 🔴
    - Source can be 'live' (real-time) or 'historical' (typical for that time)
    - When busyness data is paired with hours data, check if the location is even open at the requested time
    - If location is closed at the requested time, prioritize mentioning that over busyness data
    
    FORMATTING RULES:
    - Use ONLY plain text - NO markdown symbols (no *, **, #, ##, etc.)
    - For lists, use a simple dash and space at the start: "- Item"
    - For numbered lists, use: "1. Item", "2. Item", etc.
    - Use blank lines to separate paragraphs
    - No special formatting - just plain, clean text
    - When showing busyness, include the emoji indicators

    TONE:
    - Be concise, friendly, and helpful, casual, informal, and energetic
    - When showing busyness, include the emoji indicators
    """
    
    # Choose the appropriate system prompt
    system_prompt = voice_system_prompt if voice_mode else text_system_prompt
    
    Client = genai.Client(api_key=api_key)
    
    chat = Client.chats.create(
        model='gemini-2.0-flash',  # Faster model for quicker responses
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7
        )
    )
    
    # Combine context with user message for the thinking model
    final_prompt = f"{context}\n\nPlease provide a helpful response to the user's question."
    
    # Stream the response
    for chunk in chat.send_message_stream(final_prompt):
        if chunk.text:
            yield chunk.text


def send_user_message(api_key, user_message, personal_context="", voice_mode=False, conversation_history=None):
        logger.info("="*70)
        logger.info(f"🚀 NEW USER MESSAGE: {user_message}")
        if personal_context:
            logger.info(f"👤 PERSONAL CONTEXT: {personal_context[:200]}...")
        if conversation_history:
            logger.info(f"📚 Using conversation history: {len(conversation_history)} messages")
        logger.info("="*70)
        
        sys_prompt = """
            You are an intelligent intent classification model for Rutgers University queries.
            
            AVAILABLE DATABASE CATEGORIES:
            1. "Dining Menu" - Menu items from dining halls (DINING_HALL_MENUS table)
               - Contains: location, campus, date, meal_period, category, item
               - Example data: "Busch Dining Hall", "Breakfast", "BAGEL NUTRITION", "CINNAMON RAISIN BAGELS"
            
            2. "Dining Hours" - Operating hours for dining halls and retail food (RETAIL_FOOD_LOCATIONS table)
               - Contains: campus, name, timings, meal_swipe_available
               - Example data: "Busch Campus", "Busch Dining Hall", "Weekdays: 7:00am-9:00pm"
            
            3. "Gym Hours" - Recreation center schedules (GYM_HOURS table)
               - Contains: gym_name, campus, day, hours
               - Example data: "College Avenue Gym", "Monday", "7AM-11PM"
            
            4. "Campus Events" - Upcoming events (CAMPUS_EVENTS table)
               - Contains: name, location, date_time, link
               - Example data: "HackRU Fall 2025", "College Avenue Student Center", "Saturday, October 4"
            
            5. "Library Hours" - Library operating hours (LIBRARY_HOURS table)
               - Contains: library_name, hours for each day of week
               - Example data: "Alexander Library", "Monday: 8am - 12am"
            
            6. "Library Locations" - Library contact info (LIBRARY_LOCATIONS table)
               - Contains: name, campus, address, phone
               - Example data: "Alexander Library", "College Avenue Campus", "169 College Ave"
            
            7. "Location Busyness" - Real-time and historical crowdedness data
               - For queries about how busy/crowded a place is
               - Handles specific times: "how busy is Livingston at 2pm"
               - Handles peak queries: "what time is Livingston busiest"
               - Example queries: "is Busch crowded now", "when is the gym least busy"
            
            RESPONSE FORMAT: Return ONLY valid JSON with one or multiple categories.
            
            EXAMPLES:
            
            User: "What's for breakfast at Busch?"
            Response: {"category": ["Dining Menu"]}
            
            User: "When does the gym close today?"
            Response: {"category": ["Gym Hours"]}
            
            User: "What events are happening this weekend?"
            Response: {"category": ["Campus Events"]}
            
            User: "Where can I eat on campus and what are the hours?"
            Response: {"category": ["Dining Menu", "Dining Hours"]}
            
            User: "Is the library open on Sunday?"
            Response: {"category": ["Library Hours"]}
            
            User: "Best places to study with their locations?"
            Response: {"category": ["Library Locations", "Library Hours"]}
            
            User: "What's happening on campus today - food and events?"
            Response: {"category": ["Dining Menu", "Campus Events"]}
            
            User: "When can I work out and what's for dinner?"
            Response: {"category": ["Gym Hours", "Dining Menu"]}
            
            User: "How crowded is Livingston dining hall at 7pm?"
            Response: {"category": ["Location Busyness"]}
            
            User: "What time is the gym usually busiest?"
            Response: {"category": ["Location Busyness"]}
            
            User: "Is Busch dining hall busy right now and what are they serving?"
            Response: {"category": ["Location Busyness", "Dining Menu"]}
            
            RULES:
            - Always return valid JSON with "category" key
            - "category" value is an array of strings
            - Use exact category names from the list above
            - Select ALL relevant categories for the query
            - If no categories match, return: {"category": ["General"]}
            - For busyness queries, ALWAYS include "Location Busyness" even if other categories apply
            """

        Client = genai.Client(api_key=api_key)

        chat = Client.chats.create(
            model='gemini-2.0-flash',
            config=types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=0.7
            )
        )

        # Step 1: Get intent classification
        logger.info("🤖 STEP 1: Calling intent classification model...")
        intent_response = chat.send_message(user_message)
        intent_text = intent_response.text
        logger.info(f"📋 Intent Response: {intent_text}")
        
        # Step 2: Parse intent and determine if SQL is needed
        logger.info("🔍 STEP 2: Parsing intent and checking if SQL needed...")
        try:
            # Strip markdown code fences if present
            cleaned_intent = intent_text.strip()
            if cleaned_intent.startswith('```'):
                # Remove opening fence (```json or ```)
                lines = cleaned_intent.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                # Remove closing fence
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned_intent = '\n'.join(lines).strip()
            
            intent_data = json.loads(cleaned_intent)
            requires_sql = "category" in intent_data
            logger.info(f"✅ Intent parsed successfully: {intent_data}")
            logger.info(f"🗄️  SQL Required: {requires_sql}")
        except json.JSONDecodeError as e:
            # If JSON parsing fails, treat as general question
            logger.warning(f"⚠️  Failed to parse intent JSON: {e}")
            logger.warning(f"Raw intent text: {intent_text}")
            logger.info("💬 Treating as general question (no database query)")
            requires_sql = False
            intent_data = None
        
        # Step 3: Determine what data needs to be fetched
        categories = intent_data.get('category', []) if intent_data else []
        needs_sql = any(cat in ["Dining Menu", "Dining Hours", "Gym Hours", "Campus Events", "Library Hours", "Library Locations"] for cat in categories)
        needs_busyness = "Location Busyness" in categories
        
        sql_response = None
        busyness_response = None
        
        if needs_busyness and needs_sql:
            # CONCURRENT EXECUTION: Run both queries in parallel using ThreadPoolExecutor
            logger.info("🔀 STEP 3: Running parallel queries (Busyness + Database)...")
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both tasks
                future_busyness = executor.submit(query_busyness, user_message)
                future_sql = executor.submit(query_snowflake, intent_data, user_message)
                
                # Wait for both to complete
                busyness_response = future_busyness.result()
                sql_response = future_sql.result()
            
            logger.info(f"📊 Busyness Status: {busyness_response.get('status')}")
            logger.info(f"📊 SQL Response Status: {sql_response.get('status')}")
            
        elif needs_busyness:
            # Only busyness needed
            logger.info("🗺️  STEP 3: Querying location busyness...")
            busyness_response = query_busyness(user_message)
            logger.info(f"📊 Busyness Status: {busyness_response.get('status')}")
            
        elif needs_sql:
            # Only SQL needed
            logger.info("🗄️  STEP 3: Querying Snowflake database...")
            sql_response = query_snowflake(intent_data, user_message)
            logger.info(f"📊 SQL Response Status: {sql_response.get('status')}")
            if sql_response.get('status') == 'success':
                data_summary = {k: len(v['data']) for k, v in sql_response.get('data', {}).items()}
                logger.info(f"📈 Data retrieved: {data_summary}")
        else:
            logger.info("⏭️  STEP 3: No database or busyness query needed")
        
        # Step 4: Assemble final context
        logger.info("🔧 STEP 4: Assembling context for thinking model...")
        final_context = assemble_final_context(user_message, intent_text, sql_response, personal_context, busyness_response, conversation_history)
        logger.info(f"📝 Context length: {len(final_context)} characters")
        
        # Step 5: Get final response from thinking model
        logger.info("🧠 STEP 5: Generating final response with thinking model...")
        if voice_mode:
            logger.info("🎤 Using VOICE MODE system prompt")
        final_response = get_thinking_model_response(api_key, user_message, final_context, voice_mode)
        logger.info(f"✅ Final response generated ({len(final_response)} characters)")
        logger.info("="*70)
        
        return final_response


def send_user_message_stream(api_key, user_message, personal_context="", voice_mode=False, conversation_history=None):
    """
    Streaming version of send_user_message - yields chunks of response as they're generated.
    
    Args:
        api_key: Gemini API key
        user_message: User message
        personal_context: Optional personal context string
        voice_mode: Whether this is a voice conversation
        conversation_history: List of previous messages
        
    Yields:
        str: Chunks of the assistant's response
    """
    logger.info("="*70)
    logger.info(f"🌊 STREAMING USER MESSAGE: {user_message}")
    if personal_context:
        logger.info(f"👤 PERSONAL CONTEXT: {personal_context[:200]}...")
    if conversation_history:
        logger.info(f"📚 Using conversation history: {len(conversation_history)} messages")
    logger.info("="*70)
    
    # Follow the same pipeline as send_user_message but stream the final response
    sys_prompt = """
        You are an intelligent intent classification model for Rutgers University queries.
        
        AVAILABLE DATABASE CATEGORIES:
        1. "Dining Menu" - Menu items from dining halls (DINING_HALL_MENUS table)
           - Contains: location, campus, date, meal_period, category, item
           - Example data: "Busch Dining Hall", "Breakfast", "BAGEL NUTRITION", "CINNAMON RAISIN BAGELS"
        
        2. "Dining Hours" - Operating hours for dining halls and retail food (RETAIL_FOOD_LOCATIONS table)
           - Contains: campus, name, timings, meal_swipe_available
           - Example data: "Busch Campus", "Busch Dining Hall", "Weekdays: 7:00am-9:00pm"
        
        3. "Gym Hours" - Recreation center schedules (GYM_HOURS table)
           - Contains: gym_name, campus, day, hours
           - Example data: "College Avenue Gym", "Monday", "7AM-11PM"
        
        4. "Campus Events" - Upcoming events (CAMPUS_EVENTS table)
           - Contains: name, location, date_time, link
           - Example data: "HackRU Fall 2025", "College Avenue Student Center", "Saturday, October 4"
        
        5. "Library Hours" - Library operating hours (LIBRARY_HOURS table)
           - Contains: library_name, hours for each day of week
           - Example data: "Alexander Library", "Monday: 8am - 12am"
        
        6. "Library Locations" - Library contact info (LIBRARY_LOCATIONS table)
           - Contains: name, campus, address, phone
           - Example data: "Alexander Library", "College Avenue Campus", "169 College Ave"
        
        7. "Location Busyness" - Real-time and historical crowdedness data
           - For queries about how busy/crowded a place is
           - Handles specific times: "how busy is Livingston at 2pm"
           - Handles peak queries: "what time is Livingston busiest"
           - Example queries: "is Busch crowded now", "when is the gym least busy"
        
        RESPONSE FORMAT: Return ONLY valid JSON with one or multiple categories.
        
        RULES:
        - Always return valid JSON with "category" key
        - "category" value is an array of strings
        - Use exact category names from the list above
        - Select ALL relevant categories for the query
        - If no categories match, return: {"category": ["General"]}
        - For busyness queries, ALWAYS include "Location Busyness" even if other categories apply
        """

    Client = genai.Client(api_key=api_key)

    chat = Client.chats.create(
        model='gemini-2.0-flash',
        config=types.GenerateContentConfig(
        system_instruction=sys_prompt,
        temperature=0.7
        )
    )

    # Step 1: Get intent classification
    logger.info("🤖 STEP 1: Calling intent classification model...")
    intent_response = chat.send_message(user_message)
    intent_text = intent_response.text
    logger.info(f"📋 Intent Response: {intent_text}")
    
    # Step 2: Parse intent and determine if SQL is needed
    logger.info("🔍 STEP 2: Parsing intent and checking if SQL needed...")
    try:
        # Strip markdown code fences if present
        cleaned_intent = intent_text.strip()
        if cleaned_intent.startswith('```'):
            # Remove opening fence (```json or ```)
            lines = cleaned_intent.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            # Remove closing fence
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned_intent = '\n'.join(lines).strip()
        
        intent_data = json.loads(cleaned_intent)
        requires_sql = "category" in intent_data
        logger.info(f"✅ Intent parsed successfully: {intent_data}")
        logger.info(f"🗄️  SQL Required: {requires_sql}")
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️  Failed to parse intent JSON: {e}")
        logger.warning(f"Raw intent text: {intent_text}")
        logger.info("💬 Treating as general question (no database query)")
        requires_sql = False
        intent_data = None
    
    # Step 3: Determine what data needs to be fetched
    categories = intent_data.get('category', []) if intent_data else []
    needs_sql = any(cat in ["Dining Menu", "Dining Hours", "Gym Hours", "Campus Events", "Library Hours", "Library Locations"] for cat in categories)
    needs_busyness = "Location Busyness" in categories
    
    sql_response = None
    busyness_response = None
    
    if needs_busyness and needs_sql:
        # CONCURRENT EXECUTION: Run both queries in parallel
        logger.info("🔀 STEP 3: Running parallel queries (Busyness + Database)...")
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_busyness = executor.submit(query_busyness, user_message)
            future_sql = executor.submit(query_snowflake, intent_data, user_message)
            
            busyness_response = future_busyness.result()
            sql_response = future_sql.result()
        
        logger.info(f"📊 Busyness Status: {busyness_response.get('status')}")
        logger.info(f"📊 SQL Response Status: {sql_response.get('status')}")
        
    elif needs_busyness:
        logger.info("🗺️  STEP 3: Querying location busyness...")
        busyness_response = query_busyness(user_message)
        logger.info(f"📊 Busyness Status: {busyness_response.get('status')}")
        
    elif needs_sql:
        logger.info("🗄️  STEP 3: Querying Snowflake database...")
        sql_response = query_snowflake(intent_data, user_message)
        logger.info(f"📊 SQL Response Status: {sql_response.get('status')}")
        if sql_response.get('status') == 'success':
            data_summary = {k: len(v['data']) for k, v in sql_response.get('data', {}).items()}
            logger.info(f"📈 Data retrieved: {data_summary}")
    else:
        logger.info("⏭️  STEP 3: No database or busyness query needed")
    
    # Step 4: Assemble final context
    logger.info("🔧 STEP 4: Assembling context for thinking model...")
    final_context = assemble_final_context(user_message, intent_text, sql_response, personal_context, busyness_response, conversation_history)
    logger.info(f"📝 Context length: {len(final_context)} characters")
    
    # Step 5: Stream final response from thinking model
    logger.info("🌊 STEP 5: Streaming final response with thinking model...")
    if voice_mode:
        logger.info("🎤 Using VOICE MODE system prompt")
    
    for chunk in get_thinking_model_response_stream(api_key, user_message, final_context, voice_mode):
        yield chunk
    
    logger.info("✅ Stream completed")
    logger.info("="*70)


def send_user_message_with_history(api_key, user_message, history):
    """
    Send a message with conversation history to maintain context.
    Implements a sliding window of last 20 messages.
    
    Args:
        api_key: Gemini API key
        user_message: Current user message
        history: List of previous messages [{'role': 'user'|'assistant', 'content': '...'}]
    
    Returns:
        str: Assistant's response
    """
    system_prompt = """
    You are a helpful Rutgers University assistant with access to information about:
    - Dining menus across campus
    - Dining hall and restaurant hours
    - Gym hours and facilities
    - Campus events
    - General Rutgers information
    
    When the SQL database is not set up yet, use your knowledge to provide helpful answers 
    to general questions about Rutgers. If the question specifically requires real-time data 
    from the database (like current menu items or specific hours), politely explain that the 
    database connection is still being configured.
    
    Be concise, friendly, and helpful. Format your responses clearly.
    Maintain conversation context and remember what the user has asked before.
    """
    
    Client = genai.Client(api_key=api_key)
    
    # Create a new chat session
    chat = Client.chats.create(
        model='gemini-2.0-flash',  # Faster model for quicker responses
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7
        )
    )
    
    # Apply sliding window - keep only last 20 messages
    if len(history) > 20:
        history = history[-20:]
    
    # Build conversation context as a formatted string
    if history:
        context_parts = ["Previous conversation:"]
        for msg in history:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            context_parts.append(f"{role_label}: {msg['content']}")
        context_parts.append(f"\nCurrent question from User: {user_message}")
        full_prompt = "\n".join(context_parts)
    else:
        full_prompt = user_message
    
    # Send the message with context
    response = chat.send_message(full_prompt)
    
    return response.text
