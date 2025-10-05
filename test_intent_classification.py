#!/usr/bin/env python3
"""
Test the updated intent classification with multi-shot prompting
"""
import os
from dotenv import load_dotenv
from gemini.chat_pipeline_class import send_user_message

load_dotenv()

def test_intent_classification():
    """Test various user queries to see intent classification"""
    
    api_key = os.getenv('GEMINI_API_KEY')
    
    test_queries = [
        "What's for breakfast at Busch?",
        "When does the gym close today?",
        "What events are happening this weekend?",
        "Where can I eat on campus and what are the hours?",
        "Is the library open on Sunday?",
        "Best places to study with their locations?",
        "What's happening on campus today - food and events?",
        "When can I work out and what's for dinner?",
    ]
    
    print("🧪 Testing Intent Classification with Multi-Shot Prompting\n")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 70)
        try:
            response = send_user_message(api_key, query)
            print(f"✅ Response: {response[:200]}...")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        print()

if __name__ == "__main__":
    test_intent_classification()
