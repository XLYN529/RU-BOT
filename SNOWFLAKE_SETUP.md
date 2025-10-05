# ❄️ Snowflake Integration Setup

## ✅ Completed Steps

1. **Environment Variables** - Added Snowflake credentials to `.env`
2. **Query Function** - Implemented `query_snowflake()` in `chat_pipeline_class.py`
3. **Dependencies** - Added `snowflake-connector-python` to requirements
4. **Test Script** - Created `test_snowflake.py` for connection testing

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install backend dependencies (includes Snowflake connector)
cd backend
pip install -r requirements.txt

# Or install in main project
pip install -r requirements.txt
```

### 2. Test Snowflake Connection

```bash
python3 test_snowflake.py
```

This will:
- ✅ Test connection to Snowflake
- ✅ List all available tables
- ✅ Show row counts for each table
- ✅ Display sample data

### 3. Start the Backend

```bash
cd backend
python3 main.py
```

Backend will run on: `http://localhost:8000`

### 4. Start the Frontend

```bash
cd chat-frontend
npm install  # First time only
npm run dev
```

Frontend will run on: `http://localhost:5173`

---

## 📊 Database Schema

Your Snowflake database has these tables:

### **DINING_MENUS**
- `LOCATION` - Dining hall name
- `CAMPUS` - Campus location
- `DATE` - Menu date
- `DAY_OF_WEEK` - Day name
- `MEAL_PERIOD` - Breakfast/Lunch/Dinner
- `CATEGORY` - Food category
- `ITEM` - Menu item name

### **GYM_HOURS**
- `GYM_NAME` - Gym facility name
- `CAMPUS` - Campus location
- `DAY` - Day of week
- `HOURS` - Operating hours

### **CAMPUS_EVENTS**
- `NAME` - Event name
- `LOCATION` - Event location
- `DATE_TIME` - Event date/time
- `LINK` - Registration link

### **LIBRARY_HOURS**
- `LIBRARY_NAME` - Library name
- `SUNDAY` through `SATURDAY` - Hours for each day

### **LIBRARY_LOCATIONS**
- `NAME` - Library name
- `CAMPUS` - Campus location
- `ADDRESS` - Physical address
- `PHONE` - Contact number

### **RETAIL_FOOD**
- `CAMPUS` - Campus location
- `NAME` - Restaurant/cafe name
- `TIMINGS` - Operating hours
- `MEAL_SWIPE_AVAILABLE` - Yes/No

---

## 🔍 How It Works

### Query Flow:

1. **User asks a question** → Frontend sends to backend
2. **Intent Classification** → Gemini Flash identifies categories
3. **SQL Query** → `query_snowflake()` fetches relevant data
4. **Context Assembly** → Combines user question + intent + data
5. **Final Response** → Gemini Thinking model generates answer

### Example Categories:

- `"Rutgers Dining Menu"` → Queries DINING_MENUS
- `"Rutgers Dining Hall"` or `"Hours"` → Queries RETAIL_FOOD
- `"Gym"` or `"Recreation"` → Queries GYM_HOURS
- `"Event"` → Queries CAMPUS_EVENTS
- `"Library"` → Queries LIBRARY_HOURS + LIBRARY_LOCATIONS

---

## 🧪 Testing

### Test Snowflake Connection:
```bash
python3 test_snowflake.py
```

### Test Full Pipeline:
```bash
python3 test_pipeline.py
```

### Test Backend API:
```bash
# Start backend
cd backend
python3 main.py

# In another terminal, test the endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is on the menu today?"}'
```

---

## 🔧 Troubleshooting

### Connection Issues:
- Verify credentials in `.env` are correct
- Check Snowflake account is active
- Ensure warehouse is running

### Query Issues:
- Verify table names match exactly (case-sensitive)
- Check column names in your Snowflake tables
- Review query logs in `chat_pipeline_class.py`

### Backend Issues:
- Check logs: Backend prints detailed error messages
- Verify all dependencies installed: `pip install -r backend/requirements.txt`
- Ensure `.env` file is in project root

---

## 📝 Environment Variables

Your `.env` file should contain:

```env
# Gemini API
GEMINI_API_KEY=your_key_here

# Snowflake Connection
SNOWFLAKE_USER=XLYN529
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=VWYFDSC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=RUTGERS
SNOWFLAKE_SCHEMA=PUBLIC
```

---

## ✅ Integration Complete!

Your system is now fully integrated:
- ✅ Snowflake database connected
- ✅ Gemini AI integrated
- ✅ Backend API ready
- ✅ Frontend UI ready

**Next step: Run the test script and start the application!** 🚀
