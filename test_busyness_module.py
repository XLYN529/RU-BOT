"""
Simple test to verify busyness module works independently.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_busyness_module():
    """Test busyness module functions directly"""
    
    print("="*80)
    print("🧪 TESTING BUSYNESS MODULE")
    print("="*80)
    
    # Check if API key is available
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("❌ API_KEY not found in .env")
        return
    
    print("✅ API_KEY found\n")
    
    # Test 1: Import busyness helper
    print("Test 1: Importing busyness_helper...")
    try:
        from gmaps.busyness_helper import (
            get_busyness_at_time,
            find_peak_time,
            extract_busyness_query_type
        )
        print("✅ Successfully imported busyness_helper\n")
    except Exception as e:
        print(f"❌ Failed to import: {e}\n")
        return
    
    # Test 2: Query type extraction
    print("Test 2: Query type extraction...")
    test_queries = {
        "How busy is Livingston at 2pm": "specific_time",
        "What time is Busch busiest": "peak_time",
        "Is the gym crowded now": "current"
    }
    
    for query, expected in test_queries.items():
        result = extract_busyness_query_type(query)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{query}' -> {result} (expected: {expected})")
    
    print()
    
    # Test 3: Get busyness at time
    print("Test 3: Getting busyness data (this will make API calls)...")
    try:
        result = get_busyness_at_time("How busy is College Ave Student Center right now")
        print(f"  Status: {result.get('status')}")
        print(f"  Location: {result.get('location')}")
        print(f"  Popularity: {result.get('popularity')}")
        print(f"  Message: {result.get('message')}")
        print("  ✅ Busyness query executed\n")
    except Exception as e:
        print(f"  ❌ Error: {e}\n")
    
    # Test 4: Find peak time
    print("Test 4: Finding peak times (this will make multiple API calls)...")
    try:
        result = find_peak_time("College Ave Student Center")
        print(f"  Status: {result.get('status')}")
        print(f"  Location: {result.get('location')}")
        print(f"  Message: {result.get('message')}")
        if result.get('peak_hours'):
            print(f"  Top 3 busy times:")
            for i, hour in enumerate(result['peak_hours'][:3], 1):
                print(f"    {i}. {hour['time_str']} - {hour['popularity']}%")
        print("  ✅ Peak time query executed\n")
    except Exception as e:
        print(f"  ❌ Error: {e}\n")
    
    print("="*80)
    print("✅ MODULE TESTING COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_busyness_module()
