"""
RU AI Assistant - Basic Version
A simple chatbot for Rutgers University using Google Gemini API
"""

from google import genai
from google.genai import types
import os

class RUAIAssistant:
    def __init__(self, api_key):
        """Initialize the RU AI Assistant with Gemini API"""
        os.environ["GEMINI_API_KEY"] = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = 'gemini-2.0-flash'
        
        # System instruction for RU-specific responses
        self.system_instruction = """You are an AI assistant for Rutgers University students. 
        You help with:
        - Course information and registration
        - Campus locations and navigation
        - Student services and resources
        - Academic policies and procedures
        - Campus events and activities
        
        Always be helpful, friendly, and provide accurate Rutgers-specific information when possible.
        If you don't know something specific to Rutgers, be honest and suggest where they can find the information."""
        
        # Initialize chat
        self.chat = None
    
    def start_chat(self):
        """Start a new chat session"""
        self.chat = self.client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.7
            )
        )
        print("RU AI Assistant: Hello! I'm your Rutgers University AI Assistant. How can I help you today?")
    
    def send_message(self, message):
        """Send a message and get response"""
        if not self.chat:
            self.start_chat()
        
        response = self.chat.send_message(message)
        return response.text
    
    def chat_loop(self):
        """Interactive chat loop"""
        self.start_chat()
        
        print("\nCommands:")
        print("- Type your question normally")
        print("- Type 'exit', 'quit', or 'bye' to end the conversation\n")
        
        while True:
            user_input = input("\nYou: ")
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\nRU AI Assistant: Goodbye! R U Rah Rah!")
                break
            
            if not user_input.strip():
                continue
            
            try:
                response = self.send_message(user_input)
                print(f"\nRU AI Assistant: {response}")
            except Exception as e:
                print(f"\nError: {str(e)}")

# Main execution
if __name__ == "__main__":
    API_KEY = "AIzaSyBIjc7LaE-OdemNhmCkkBRD2QPnbNMJy5I"
    
    print("=" * 60)
    print("RU AI ASSISTANT - Rutgers University Chatbot")
    print("=" * 60)
    
    assistant = RUAIAssistant(API_KEY)
    assistant.chat_loop()
