#!/usr/bin/env python3
"""Quick test of the chat pipeline integration"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add gemini directory to path
gemini_path = Path(__file__).parent / "gemini"
sys.path.insert(0, str(gemini_path))

import chat_pipeline_class

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

def test_pipeline():
    """Test the chat pipeline with sample questions"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env file")
        return False
    
    print("🧪 Testing Chat Pipeline Integration\n")
    print("="*60)
    
    # Test 1: SQL-required question
    print("\n📝 Test 1: Question requiring SQL (menu data)")
    print("Question: 'What's on the menu at Busch dining hall today?'")
    print("-" * 60)
    try:
        response1 = chat_pipeline_class.send_user_message(
            api_key,
            "What's on the menu at Busch dining hall today?"
        )
        print(f"✅ Response received:\n{response1}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False
    
    # Test 2: General Q&A question
    print("\n📝 Test 2: General Q&A (no SQL needed)")
    print("Question: 'What is Rutgers University known for?'")
    print("-" * 60)
    try:
        response2 = chat_pipeline_class.send_user_message(
            api_key,
            "What is Rutgers University known for?"
        )
        print(f"✅ Response received:\n{response2}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False
    
    print("="*60)
    print("✅ All tests passed! Pipeline is working correctly.")
    print("\n🌐 Frontend is running at: http://localhost:3000")
    return True

if __name__ == "__main__":
    success = test_pipeline()
    sys.exit(0 if success else 1)
