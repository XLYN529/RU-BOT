"""
Test script for busyness integration with Gemini pipeline.
"""

import os
from dotenv import load_dotenv
from gemini.chat_pipeline_class import send_user_message

load_dotenv()

def test_busyness_queries():
    """Test various busyness query scenarios"""
    
    api_key = os.getenv("API_KEY")
    
    if not api_key:
        print("❌ API_KEY not found in .env")
        return
    
    test_queries = [
        # Test 1: Specific time busyness
        "How busy is Livingston dining hall at 2pm today?",
        
        # Test 2: Current busyness
        "Is Busch Student Center crowded right now?",
        
        # Test 3: Peak time query
        "What time is the College Ave gym usually busiest?",
        
        # Test 4: Combined query (busyness + menu)
        "How crowded is Livingston at 7pm and what are they serving for dinner?",
        
        # Test 5: Combined query (busyness + hours)
        "Is the gym busy at 9pm and is it even open then?",
    ]
    
    print("="*80)
    print("🧪 TESTING BUSYNESS INTEGRATION")
    print("="*80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {query}")
        print(f"{'='*80}")
        
        try:
            response = send_user_message(api_key, query)
            print(f"\n✅ RESPONSE:\n{response}\n")
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}\n")
        
        print("-"*80)

if __name__ == "__main__":
    test_busyness_queries()
