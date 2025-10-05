#!/usr/bin/env python3
"""
Test Snowflake connection and query functionality
"""
import os
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

def test_connection():
    """Test basic Snowflake connection"""
    print("🔍 Testing Snowflake connection...")
    
    try:
        conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE'),
            schema=os.getenv('SNOWFLAKE_SCHEMA')
        )
        
        cursor = conn.cursor()
        
        # Test query
        print("\n✅ Connection successful!")
        print(f"   Database: {os.getenv('SNOWFLAKE_DATABASE')}")
        print(f"   Schema: {os.getenv('SNOWFLAKE_SCHEMA')}")
        
        # List all tables
        print("\n📊 Available tables:")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        for table in tables:
            print(f"   - {table[1]}")  # table[1] is the table name
        
        # Test each table
        print("\n🔢 Row counts:")
        
        tables_to_check = [
            'DINING_HALL_MENUS',
            'GYM_HOURS',
            'CAMPUS_EVENTS',
            'LIBRARY_HOURS',
            'LIBRARY_LOCATIONS',
            'RETAIL_FOOD_LOCATIONS'
        ]
        
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   {table}: {count} rows")
            except Exception as e:
                print(f"   {table}: ❌ Error - {str(e)}")
        
        # Test sample query
        print("\n📝 Sample query (first 3 dining menu items):")
        cursor.execute("SELECT * FROM DINING_HALL_MENUS LIMIT 3")
        rows = cursor.fetchall()
        for row in rows:
            print(f"   {row}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()
