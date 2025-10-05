"""
Busyness query helper for integration with Gemini pipeline.
Provides functions for:
- Checking busyness at specific times
- Finding peak busy times for a location
- Validating time queries against operating hours
"""

from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import logging
import os
import sys

# Handle imports whether called as module or directly
try:
    from .rutgers_busyness import (
        resolve_and_measure_at,
        _parse_when,
        _normalize_place_query,
        _get_popularity_for_id_at,
        _text_search_first,
        _rutgers_rectangle,
        RUTGERS_RECT_RADIUS_M,
        API_KEY
    )
except ImportError:
    from rutgers_busyness import (
        resolve_and_measure_at,
        _parse_when,
        _normalize_place_query,
        _get_popularity_for_id_at,
        _text_search_first,
        _rutgers_rectangle,
        RUTGERS_RECT_RADIUS_M,
        API_KEY
    )

logger = logging.getLogger(__name__)


def get_busyness_at_time(query_text: str) -> Dict:
    """
    Get busyness for a location at a specific time.
    
    Args:
        query_text: Natural language query like "how busy is Livingston at 2pm"
    
    Returns:
        dict with keys:
            - location: str (normalized location name)
            - time: datetime object
            - popularity: int (0-100) or None
            - source: str ('live', 'historical', 'unavailable')
            - status: str ('success', 'unavailable', 'error')
            - message: str (human-readable result)
    """
    try:
        when = _parse_when(query_text)
        # Use query as-is for dining/food places, normalize for general locations
        target = query_text
        if not any(kw in query_text.lower() for kw in ['dining', 'cafe', 'starbucks', 'restaurant', 'food', 'market']):
            target = _normalize_place_query(query_text)
        
        result = resolve_and_measure_at(target, when)
        
        if not result:
            return {
                "location": target,
                "time": when,
                "popularity": None,
                "source": "unavailable",
                "status": "error",
                "message": f"Could not find location: {target}"
            }
        
        val = result.get("popularity")
        src = result.get("source")
        
        # Generate human-readable message
        if val is None:
            message = "Busyness data unavailable"
            status = "unavailable"
        else:
            # Categorize busyness level
            if val < 30:
                level = "🟢 light"
            elif val < 60:
                level = "🟡 medium"
            elif val < 85:
                level = "🟠 high"
            else:
                level = "🔴 very high"
            
            time_desc = "now" if abs((when - datetime.now()).total_seconds()) < 1800 else when.strftime("%I:%M %p")
            message = f"{result['name']} is {val}% busy ({level}) at {time_desc}"
            status = "success"
        
        return {
            "location": result.get("name", target),
            "time": when,
            "popularity": val,
            "source": src,
            "status": status,
            "message": message,
            "method": result.get("method"),
            "raw_result": result
        }
    
    except Exception as e:
        logger.error(f"Error getting busyness: {e}")
        return {
            "location": None,
            "time": None,
            "popularity": None,
            "source": "unavailable",
            "status": "error",
            "message": f"Error: {str(e)}"
        }


def find_peak_time(location_query: str, day_offset: int = 0) -> Dict:
    """
    Find the busiest time(s) for a location by analyzing historical data.
    
    Args:
        location_query: Location name (e.g., "Livingston Dining Hall")
        day_offset: 0 for today, 1 for tomorrow
    
    Returns:
        dict with keys:
            - location: str
            - peak_hours: List[dict] with 'hour', 'popularity', 'time_str'
            - average_busy_time: str (formatted time range)
            - status: str
            - message: str
    """
    try:
        # Use query as-is first, don't normalize (to avoid forcing Student Centers)
        # If it contains specific keywords like "dining", "cafe", "starbucks", use raw query
        target = location_query
        if not any(kw in location_query.lower() for kw in ['dining', 'cafe', 'starbucks', 'restaurant', 'food', 'market', 'fast food']):
            target = _normalize_place_query(location_query)
        
        # First resolve the place
        rect = _rutgers_rectangle(RUTGERS_RECT_RADIUS_M)
        top = _text_search_first(target, rect)
        
        if not top:
            return {
                "location": target,
                "peak_hours": [],
                "average_busy_time": None,
                "status": "error",
                "message": f"Could not find location: {target}"
            }
        
        pid = top["id"]
        name = (top.get("displayName") or {}).get("text") or target
        
        # Analyze busyness for every hour from 7am to 11pm
        now = datetime.now()
        base_date = now + timedelta(days=day_offset)
        
        hourly_data = []
        for hour in range(7, 23):  # 7am to 10pm
            test_time = base_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # Get historical data for this hour
            val, src, raw = _get_popularity_for_id_at(pid, test_time, allow_live=False)
            
            if isinstance(val, int):
                time_str = test_time.strftime("%I:%M %p").lstrip("0")
                hourly_data.append({
                    "hour": hour,
                    "popularity": val,
                    "time_str": time_str,
                    "datetime": test_time
                })
        
        if not hourly_data:
            return {
                "location": name,
                "peak_hours": [],
                "average_busy_time": None,
                "status": "unavailable",
                "message": f"No historical busyness data available for {name}"
            }
        
        # Sort by popularity
        sorted_data = sorted(hourly_data, key=lambda x: x["popularity"], reverse=True)
        
        # Get top 3 busiest hours
        top_3 = sorted_data[:3]
        
        # Find continuous peak window (consecutive hours with high busyness)
        threshold = sorted_data[0]["popularity"] * 0.85  # Within 85% of peak
        peak_window = []
        
        for item in hourly_data:
            if item["popularity"] >= threshold:
                peak_window.append(item)
        
        # Format message
        if top_3:
            peak = top_3[0]
            message = f"{name} is typically busiest at {peak['time_str']} ({peak['popularity']}% busy)"
            
            if len(peak_window) > 1:
                times = [p["time_str"] for p in peak_window]
                peak_range = f"{times[0]} - {times[-1]}"
                message += f". Peak busy period: {peak_range}"
        else:
            message = f"Could not determine peak times for {name}"
        
        return {
            "location": name,
            "peak_hours": top_3,
            "all_hours": hourly_data,
            "peak_window": peak_window,
            "status": "success",
            "message": message
        }
    
    except Exception as e:
        logger.error(f"Error finding peak time: {e}")
        return {
            "location": None,
            "peak_hours": [],
            "average_busy_time": None,
            "status": "error",
            "message": f"Error: {str(e)}"
        }


def extract_busyness_query_type(query: str) -> str:
    """
    Determine if query is asking for:
    - 'specific_time': busyness at a specific time
    - 'peak_time': what time is busiest
    - 'current': busyness right now
    
    Args:
        query: User query text
    
    Returns:
        str: query type
    """
    query_lower = query.lower()
    
    # Check for peak time queries
    peak_keywords = ["busiest", "most crowded", "peak time", "peak hour", "most busy"]
    if any(kw in query_lower for kw in peak_keywords):
        return "peak_time"
    
    # Check for time-specific queries
    time_keywords = ["at", "around", "pm", "am", "o'clock"]
    if any(kw in query_lower for kw in time_keywords) and "now" not in query_lower:
        return "specific_time"
    
    # Default to current
    return "current"


def extract_location_from_query(query: str) -> Optional[str]:
    """
    Extract location name from busyness query.
    
    Args:
        query: User query text
    
    Returns:
        str: Location name or None
    """
    query_lower = query.lower()
    
    # Common Rutgers locations
    locations = {
        "livingston": "Livingston Student Center",
        "livi": "Livingston Student Center",
        "busch": "Busch Student Center",
        "college ave": "College Ave Student Center",
        "cac": "College Ave Student Center",
        "cook": "Cook Student Center",
        "douglass": "Douglass Student Center",
        "alexander": "Alexander Library",
        "lsc": "Livingston Student Center"
    }
    
    for key, value in locations.items():
        if key in query_lower:
            return value
    
    return None
