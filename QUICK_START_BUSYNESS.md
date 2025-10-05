# Quick Start: Busyness Feature

## Setup

### 1. Add Google Places API Key to `.env`
```bash
# Add this to your .env file
API_KEY=your_google_places_api_key_here
```

### 2. Install Dependencies (if needed)
```bash
pip install populartimes
```

### 3. Test the Module
```bash
# Test busyness module independently
python test_busyness_module.py

# Test full integration
python test_busyness_integration.py
```

### 4. Start the Backend
```bash
cd backend
uvicorn main:app --reload
```

## Example Queries

### Specific Time
- "How busy is Livingston dining hall at 2pm?"
- "Is Busch Student Center crowded at 7pm tonight?"

### Peak Times
- "What time is the College Ave gym busiest?"
- "When is Livingston least crowded?"

### Current
- "How crowded is Busch right now?"
- "Is the gym busy?"

### Combined (uses ThreadPoolExecutor)
- "Is Livingston busy at 7pm and what's for dinner?"
- "How crowded is the gym at 9pm and is it even open?"

## How It Works

1. **Intent Classification** → Gemini identifies "Location Busyness" category
2. **Concurrent Execution** → If busyness + database query needed, runs in parallel via ThreadPoolExecutor
3. **No Manual Threading** → You asked about promises - ThreadPoolExecutor handles all synchronization automatically
4. **Automatic Hours Check** → When checking busyness, can automatically verify location is open

## Key Features

✅ **Parallel Execution** - Busyness API + Snowflake queries run simultaneously  
✅ **Peak Time Analysis** - Finds busiest hours by analyzing historical data  
✅ **Time Parsing** - Understands "2pm", "tonight at 7", "tomorrow at 9am"  
✅ **Smart Fallbacks** - Uses sub-venues or area estimation if direct data unavailable  
✅ **No Race Conditions** - `future.result()` blocks until data ready

## Architecture Decision

You asked about promises in Python - we used **ThreadPoolExecutor** instead:

```python
# Both run at the same time
with ThreadPoolExecutor(max_workers=2) as executor:
    future_busyness = executor.submit(query_busyness, message)
    future_sql = executor.submit(query_snowflake, intent, message)
    
    # Wait for BOTH to finish (no race condition)
    busyness = future_busyness.result()  # blocks until done
    sql = future_sql.result()            # blocks until done

# Final response only generated after both complete
```

This is cleaner than promises and works perfectly with your synchronous code.

## Need Help?

See `BUSYNESS_INTEGRATION.md` for comprehensive documentation.
