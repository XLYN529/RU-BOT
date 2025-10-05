# Busyness Integration Documentation

## Overview

The RU Assistant now includes real-time and historical location busyness/crowdedness data using Google Places API and the `populartimes` library. The integration uses **ThreadPoolExecutor** for concurrent execution when multiple data sources are needed.

## Architecture

### Query Flow

```
User Message
    ↓
Intent Classification (Gemini 2.0 Flash)
    ↓
Determine Data Sources Needed
    ├─→ SQL Only → Query Snowflake
    ├─→ Busyness Only → Query Google Places API
    └─→ Both → CONCURRENT EXECUTION via ThreadPoolExecutor
           ├─→ Thread 1: Query Snowflake
           └─→ Thread 2: Query Google Places API
    ↓
Wait for all results (future.result())
    ↓
Assemble Context
    ↓
Final Response (Gemini Thinking Model)
```

### Key Components

#### 1. `gmaps/rutgers_busyness.py`
- **Core busyness detection script**
- Uses Google Places API Text Search to resolve locations
- Fetches live/historical popularity via `populartimes` library
- Fallback strategies: sub-venues → area-weighted estimation
- Time-aware queries with `resolve_and_measure_at()`

#### 2. `gmaps/busyness_helper.py` (NEW)
- **Integration layer for the pipeline**
- Functions:
  - `get_busyness_at_time(query)` - Get busyness at specific time
  - `find_peak_time(location)` - Analyze all hours to find busiest times
  - `extract_busyness_query_type(query)` - Classify query type

#### 3. `gemini/chat_pipeline_class.py` (MODIFIED)
- **Enhanced pipeline with busyness support**
- New category: `"Location Busyness"`
- ThreadPoolExecutor for concurrent data fetching
- Smart logic: when busyness + SQL both needed → parallel execution

## Query Types

### 1. Specific Time Queries
**Examples:**
- "How busy is Livingston at 2pm?"
- "Is Busch crowded at 7pm tonight?"
- "How crowded is the gym at 9am tomorrow?"

**Behavior:**
- Parses time from natural language
- Returns historical data for future times
- Returns live data if available for current time
- Popularity: 0-100% with emoji indicators

### 2. Peak Time Queries
**Examples:**
- "What time is Livingston busiest?"
- "When is the gym most crowded?"
- "What's the least busy time at Busch?"

**Behavior:**
- Queries historical data for every hour (7am-10pm)
- Returns top 3 busiest times
- Identifies peak busy windows (consecutive high-traffic hours)

### 3. Current Busyness
**Examples:**
- "How busy is College Ave right now?"
- "Is the gym crowded now?"

**Behavior:**
- Attempts to fetch live Google data first
- Falls back to historical data for current hour if live unavailable

## Combined Queries (Why ThreadPoolExecutor?)

### Problem
When user asks: **"Is Livingston dining hall busy at 7pm and what are they serving?"**

We need to:
1. Check busyness at 7pm (Google API calls - slow)
2. Query dining menu from Snowflake (database query - slow)

**Without concurrency:** Total time = Time₁ + Time₂ (sequential)
**With ThreadPoolExecutor:** Total time ≈ max(Time₁, Time₂) (parallel)

### Implementation

```python
if needs_busyness and needs_sql:
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_busyness = executor.submit(query_busyness, user_message)
        future_sql = executor.submit(query_snowflake, intent_data, user_message)
        
        # Wait for BOTH to complete
        busyness_response = future_busyness.result()
        sql_response = future_sql.result()
```

**Key Points:**
- Both queries run simultaneously in separate threads
- `future.result()` blocks until that specific task completes
- Final response only generated after ALL data is collected
- No "promise" needed - ThreadPoolExecutor handles synchronization

## Hours Validation

**Smart Integration:**
When asking about busyness at a specific time, the system can automatically check operating hours from the database.

**Example:**
```
User: "How busy is Livingston at 2am?"

Intent: ["Location Busyness", "Dining Hours"]

Execution (parallel):
- Thread 1: Get busyness data → "25% busy"
- Thread 2: Get hours → "Closed at 2am"

Final Response: "Livingston dining hall is closed at 2am. It typically opens at 7:00am."
```

The thinking model intelligently prioritizes the hours data when the location is closed.

## Busyness Levels

| Popularity | Level | Emoji | Description |
|-----------|-------|-------|-------------|
| 0-30% | Light | 🟢 | Not busy, good time to visit |
| 30-60% | Medium | 🟡 | Moderately busy |
| 60-85% | High | 🟠 | Very busy, expect crowds |
| 85-100% | Very High | 🔴 | Extremely crowded |

## Testing

### Test 1: Module-level test
```bash
python test_busyness_module.py
```
Tests busyness functions independently without Gemini integration.

### Test 2: Full integration test
```bash
python test_busyness_integration.py
```
Tests end-to-end pipeline with various query types.

### Test 3: Manual backend test
```bash
cd backend
uvicorn main:app --reload
```
Then send POST requests to `/api/chat`

## Configuration

### Required Environment Variables

`.env` file must contain:
```bash
# Google Maps/Places API (for busyness)
API_KEY=your_google_api_key_here

# Gemini API (for intent classification & responses)
GEMINI_API_KEY=your_gemini_api_key_here

# Snowflake (for database queries)
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
```

### Google API Setup
1. Enable **Places API (New)** in Google Cloud Console
2. Generate API key with Places API access
3. Note: `populartimes` library uses internal Google endpoints

## Intent Classification

The intent classification model now recognizes:

```json
{
  "category": ["Location Busyness"]
}
```

Or combined:
```json
{
  "category": ["Location Busyness", "Dining Menu"]
}
```

### Training Examples Added
- "How crowded is Livingston dining hall at 7pm?" → `["Location Busyness"]`
- "What time is the gym usually busiest?" → `["Location Busyness"]`
- "Is Busch busy and what's for dinner?" → `["Location Busyness", "Dining Menu"]`

## Performance Considerations

### API Rate Limits
- Google Places API: 1000 requests/day (free tier)
- Each busyness check makes 1-3 API calls
- Peak time queries make 15-20 API calls (checking every hour)

### Caching (Future Enhancement)
Consider caching:
- Historical data (changes rarely)
- Peak time analysis (stable patterns)
- Location resolution (place IDs)

### Optimization
ThreadPoolExecutor provides ~50% speedup for combined queries vs sequential execution.

## Example Conversations

### Example 1: Simple Busyness
```
User: "How busy is Livingston right now?"

Response: "Livingston Student Center is currently 45% busy 🟡 
(moderately busy). This is based on live data from Google."
```

### Example 2: Peak Time
```
User: "When is Busch Student Center busiest?"

Response: "Busch Student Center is typically busiest at:
1. 12:30 PM - 78% busy 🟠
2. 1:00 PM - 74% busy 🟠  
3. 6:30 PM - 71% busy 🟠

The peak busy period is usually from 12:00 PM - 2:00 PM."
```

### Example 3: Combined Query
```
User: "Is Livingston crowded at 7pm and what's for dinner?"

Response: "Livingston Dining Commons is 62% busy 🟠 at 7pm 
(very busy - expect some wait times).

For dinner tonight, they're serving:
- Main: Grilled Chicken, Baked Salmon
- Sides: Roasted Vegetables, Mashed Potatoes
- Vegetarian: Veggie Stir Fry
..."
```

## Error Handling

### Busyness Data Unavailable
- Returns: `"Busyness data unavailable ⚪ unknown"`
- Reasons: Location too new, no Google data, API error

### Location Not Found
- Returns: `"Could not find location: [name]"`
- Suggestion: Normalize common variations (Livi → Livingston)

### API Errors
- Gracefully handled
- System logs error
- Returns user-friendly message

## Future Enhancements

1. **Historical Trend Analysis**
   - Show busyness trends over past week
   - "Livingston is busier than usual today"

2. **Smart Recommendations**
   - "Try visiting at 3pm instead - typically 30% less busy"

3. **Multi-location Comparison**
   - "Busch is less busy than Livingston right now"

4. **Push Notifications**
   - Alert when favorite location hits target busyness level

5. **AsyncIO Migration**
   - Replace ThreadPoolExecutor with full async/await
   - Requires async Snowflake connector

## Troubleshooting

### Import Errors
```
ImportError: cannot import name 'get_busyness_at_time'
```
**Solution:** Ensure `gmaps/__init__.py` exists and path is added to sys.path

### API Key Issues
```
Error: API_KEY not found
```
**Solution:** Check `.env` file has `API_KEY=...` (for Google) and `GEMINI_API_KEY=...`

### Slow Response Times
- Check network latency to Google APIs
- Verify ThreadPoolExecutor is being used (check logs for "🔀 Running parallel queries")
- Consider reducing radius in `rutgers_busyness.py` (currently 300m)

## Logs

Enable debug logging to see execution flow:
```python
logging.basicConfig(level=logging.DEBUG)
```

Key log indicators:
- `🔀 STEP 3: Running parallel queries` - ThreadPoolExecutor active
- `🗺️ STEP 3: Querying location busyness` - Busyness only
- `🗄️ STEP 3: Querying Snowflake` - SQL only
- `⏭️ STEP 3: No database or busyness query needed` - General query
