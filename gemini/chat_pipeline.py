
import chat_pipeline_class

if __name__ == "__main__":
    API_KEY = "AIzaSyBIjc7LaE-OdemNhmCkkBRD2QPnbNMJy5I"
    
    result = chat_pipeline_class.send_user_message(
        api_key=API_KEY,
        user_message="What is best places to eat near rutgers"
    )
    
    print(f"Response: {result}")
   