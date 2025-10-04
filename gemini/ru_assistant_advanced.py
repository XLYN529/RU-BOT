"""
RU AI Assistant - Advanced Version with Google Search
A chatbot for Rutgers University with real-time search capability
"""

from google import genai
from google.genai import types
import os
from datetime import datetime

class RUAIAssistantAdvanced:
    def __init__(self, api_key):
        """Initialize advanced RU AI Assistant with search capability"""
        os.environ["GEMINI_API_KEY"] = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = 'gemini-2.0-flash'
        
        self.system_instruction = """You are an advanced AI assistant for Rutgers University.
        You can access real-time information about:
        - Current events at Rutgers
        - Course schedules and availability
        - Campus news and updates
        - Weather and transportation
        - Student resources and services
        - Academic calendar and deadlines
        
        Provide accurate, helpful, and up-to-date information. When users ask about current 
        information, use the search tool to find the latest details."""
        
        self.search_tool = {'google_search': {}}
        self.chat = None
        self.conversation_history = []
    
    def start_chat_with_search(self):
        """Start chat with Google Search enabled"""
        self.chat = self.client.chats.create(
            model=self.model,
            config={
                'tools': [self.search_tool],
                'system_instruction': self.system_instruction,
                'temperature': 0.7
            }
        )
        current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        print(f"\nRU AI Assistant (Advanced): Hello! I'm your Rutgers AI Assistant with real-time search.")
        print(f"Current time: {current_time}")
        print("I can help with current Rutgers information. What would you like to know?")
    
    def send_message(self, message):
        """Send message and get response with search capability"""
        if not self.chat:
            self.start_chat_with_search()
        
        # Add to conversation history
        self.conversation_history.append({
            'timestamp': datetime.now(),
            'user': message,
            'assistant': None
        })
        
        response = self.chat.send_message(message)
        response_text = response.candidates[0].content.parts[0].text
        
        # Update conversation history
        self.conversation_history[-1]['assistant'] = response_text
        
        return response_text
    
    def save_conversation(self, filename='conversation_history.txt'):
        """Save conversation history to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("RU AI ASSISTANT - Conversation History\n")
            f.write("=" * 60 + "\n\n")
            
            for entry in self.conversation_history:
                timestamp = entry['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}]\n")
                f.write(f"User: {entry['user']}\n")
                f.write(f"Assistant: {entry['assistant']}\n")
                f.write("-" * 60 + "\n\n")
        
        print(f"\nConversation saved to {filename}")
    
    def chat_loop(self):
        """Interactive chat loop with search"""
        self.start_chat_with_search()
        
        print("\n" + "=" * 60)
        print("COMMANDS:")
        print("  - Type your question normally")
        print("  - Type 'exit' or 'quit' to end")
        print("  - Type 'new' to start a fresh conversation")
        print("  - Type 'save' to save conversation history")
        print("=" * 60 + "\n")
        
        while True:
            user_input = input("\nYou: ")
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                save_choice = input("\nWould you like to save this conversation? (yes/no): ")
                if save_choice.lower() in ['yes', 'y']:
                    self.save_conversation()
                print("\nRU AI Assistant: Goodbye! Go Scarlet Knights!")
                break
            
            if user_input.lower() == 'new':
                self.conversation_history = []
                self.start_chat_with_search()
                continue
            
            if user_input.lower() == 'save':
                self.save_conversation()
                continue
            
            if not user_input.strip():
                continue
            
            try:
                response = self.send_message(user_input)
                print(f"\nRU AI Assistant: {response}")
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try rephrasing your question.")

# Main execution
if __name__ == "__main__":
    API_KEY = "AIzaSyBIjc7LaE-OdemNhmCkkBRD2QPnbNMJy5I"
    
    print("\n" + "=" * 60)
    print("RU AI ASSISTANT - ADVANCED VERSION")
    print("Rutgers University Chatbot with Real-Time Search")
    print("=" * 60)
    
    assistant = RUAIAssistantAdvanced(API_KEY)
    assistant.chat_loop()
