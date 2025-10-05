from google.genai import types
from google import genai
import json


class ChatSession:
    """
    Maintains a persistent Gemini chat session with automatic context retention.
    This is much more efficient than replaying history on each message.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize a new chat session.
        
        Args:
            api_key: Gemini API key
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.message_count = 0
        
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
        You have full conversation memory - you can recall any previous messages in this conversation.
        """
        
        # Create persistent chat session
        self.chat = self.client.chats.create(
            model='gemini-2.0-flash-thinking-exp-01-21',
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )
        )
    
    def send_message(self, message: str) -> str:
        """
        Send a message and get response.
        The chat session automatically maintains full conversation context.
        
        Args:
            message: User message
            
        Returns:
            str: Assistant's response
        """
        try:
            self.message_count += 1
            response = self.chat.send_message(message)
            return response.text
        except Exception as e:
            # Log the error and re-raise with more context
            error_msg = f"Gemini API error at message {self.message_count}: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise Exception(error_msg) from e
    
    def get_message_count(self) -> int:
        """Get the number of messages sent in this session."""
        return self.message_count


def query_snowflake(intent_data):
    """
    Placeholder function for Snowflake SQL queries.
    
    Args:
        intent_data: JSON object with category information from intent classification
    
    Returns:
        dict: Query results or error message
    """
    # TODO: Implement actual Snowflake connection and query logic
    return {
        "status": "not_implemented",
        "message": "SQL database not set up yet",
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
    
    Be concise, friendly, and helpful. Format your responses clearly.
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

        
        sys_prompt = """
            You are a agentic model who is really smart at understand user intent
            There are some categroies in the SQL database, here they are:
            1. Rutgers Dining Menu
            2. Rutgers Dining Hall and Retail/Restuarant Hours


            YOU CAN RESPOND WITH AS MANY CATEGORIES AS YOU NEED
            RESPOND ONLY IN JSON STRUCTURE 
            Example if Rutgers Dining menu is needed: 

            you would respond ->

            { 
            "category": "Rutgers Dining Menu",
            }

            OR IF MULTIPLE CATEGORIES ARE NEEDED, YOU CAN RESPOND LIKE THIS 
            LIKE IF THE USER ASKED BEST PLACES TO EAT ON CAMPUS, RESPOND LIKE THIS ->

            { 
            "category": 
                {
                "Rutgers Dining Menu",
                "Rutgers Dining Hall and Retail/Restuarant Hours",
                }
            }
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
        intent_response = chat.send_message(user_message)
        intent_text = intent_response.text
        
        # Step 2: Parse intent and determine if SQL is needed
        try:
            intent_data = json.loads(intent_text)
            requires_sql = "category" in intent_data
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as general question
            requires_sql = False
            intent_data = None
        
        # Step 3: Query SQL if needed (placeholder for now)
        sql_response = None
        if requires_sql:
            sql_response = query_snowflake(intent_data)
        
        # Step 4: Assemble final context
        final_context = assemble_final_context(user_message, intent_text, sql_response)
        
        # Step 5: Get final response from thinking model
        final_response = get_thinking_model_response(api_key, user_message, final_context)
        
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
