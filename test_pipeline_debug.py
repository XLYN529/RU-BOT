"""
Debug test to see what's happening in the pipeline
"""
import os
from dotenv import load_dotenv
from gemini.chat_pipeline_class import send_user_message

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ GEMINI_API_KEY not found")
    exit(1)

print("Testing a simple dining query...")
print("="*80)

query = "What's for breakfast at Busch?"
print(f"Query: {query}\n")

try:
    response = send_user_message(api_key, query)
    print("="*80)
    print("RESPONSE:")
    print(response)
    print("="*80)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
