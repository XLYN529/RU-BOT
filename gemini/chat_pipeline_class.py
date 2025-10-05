from google.genai import types
from google import genai
import json
import os
from dotenv import load_dotenv
import snowflake.connector
import logging
import traceback
from datetime import date, datetime

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    
    def send_message(self, message: str) -> str:
        """
        Send a message with full pipeline: intent classification → database query → response.
        Maintains conversation history for context.
        
        Args:
            message: User message
            
        Returns:
            str: Assistant's response with database data
        """
        try:
            self.message_count += 1
            logger.info("="*70)
            logger.info(f"💬 ChatSession Message #{self.message_count}: {message}")
            logger.info("="*70)
            
            # Use the full pipeline with intent classification and database queries
            response = send_user_message(self.api_key, message)
            
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


def assemble_final_context(user_message, intent_response, sql_response):
    """
    Assembles the final context prompt for the thinking model.
    
    Args:
        user_message: Original user question
        intent_response: Response from intent classification model
        sql_response: Response from SQL query (or None if not applicable)
    
    Returns:
        str: Assembled context for the thinking model
    """
    context_parts = []
    
    context_parts.append(f"User Question: {user_message}")
    context_parts.append(f"\nIdentified Intent/Categories: {intent_response}")
    
    if sql_response and sql_response.get("status") == "success":
        context_parts.append(f"\nDatabase Results:\n{json.dumps(sql_response['data'], indent=2)}")
    elif sql_response and sql_response.get("status") == "not_implemented":
        context_parts.append(f"\nNote: {sql_response['message']}")
    
    return "\n".join(context_parts)


def get_thinking_model_response(api_key, user_message, context):
    """
    Sends assembled context to Gemini Pro (thinking model) for final response.
    
    Args:
        api_key: Gemini API key
        user_message: Original user message
        context: Assembled context from previous steps
    
    Returns:
        str: Final response from thinking model
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
    
    FORMATTING RULES:
    - Use plain text formatting (no Markdown symbols like *, **, #, etc.)
    - Use line breaks and indentation for structure
    - Use simple dashes (-) for lists if needed
    - Be concise, friendly, and helpful
    """
    
    Client = genai.Client(api_key=api_key)
    
    chat = Client.chats.create(
        model='gemini-2.0-flash-thinking-exp-01-21',
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7
        )
    )
    
    # Combine context with user message for the thinking model
    final_prompt = f"{context}\n\nPlease provide a helpful response to the user's question."
    
    response = chat.send_message(final_prompt)
    return response.text


def send_user_message(api_key, user_message):
        logger.info("="*70)
        logger.info(f"🚀 NEW USER MESSAGE: {user_message}")
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
            
            RULES:
            - Always return valid JSON with "category" key
            - "category" value is an array of strings
            - Use exact category names from the list above
            - Select ALL relevant categories for the query
            - If no categories match, return: {"category": ["General"]}
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
            intent_data = json.loads(intent_text)
            requires_sql = "category" in intent_data
            logger.info(f"✅ Intent parsed successfully: {intent_data}")
            logger.info(f"🗄️  SQL Required: {requires_sql}")
        except json.JSONDecodeError as e:
            # If JSON parsing fails, treat as general question
            logger.warning(f"⚠️  Failed to parse intent JSON: {e}")
            logger.info("💬 Treating as general question (no database query)")
            requires_sql = False
            intent_data = None
        
        # Step 3: Query SQL if needed
        sql_response = None
        if requires_sql:
            logger.info("🗄️  STEP 3: Querying Snowflake database...")
            sql_response = query_snowflake(intent_data, user_message)
            logger.info(f"📊 SQL Response Status: {sql_response.get('status')}")
            if sql_response.get('status') == 'success':
                data_summary = {k: len(v['data']) for k, v in sql_response.get('data', {}).items()}
                logger.info(f"📈 Data retrieved: {data_summary}")
        else:
            logger.info("⏭️  STEP 3: Skipping database query (not needed)")
        
        # Step 4: Assemble final context
        logger.info("🔧 STEP 4: Assembling context for thinking model...")
        final_context = assemble_final_context(user_message, intent_text, sql_response)
        logger.info(f"📝 Context length: {len(final_context)} characters")
        
        # Step 5: Get final response from thinking model
        logger.info("🧠 STEP 5: Generating final response with thinking model...")
        final_response = get_thinking_model_response(api_key, user_message, final_context)
        logger.info(f"✅ Final response generated ({len(final_response)} characters)")
        logger.info("="*70)
        
        return final_response


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
        model='gemini-2.0-flash-thinking-exp-01-21',
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
