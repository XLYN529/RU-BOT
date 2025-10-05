# rutgers_busyness.py
# End-to-end resolver for Rutgers locations:
# 1) Resolve place by name in Rutgers rectangle (Text Search v1)
# 2) Try live/historical popularity via populartimes.get_id
# 3) If missing, scan sub-venues nearby (Nearby Search v1) and use best available
# 4) If still missing, compute area-weighted popularity from multiple POIs
#
# Requires:
#   pip install requests fastapi uvicorn git+https://github.com/m-wrzr/populartimes
#
# References: Places API v1 Text Search and Nearby Search require X-Goog-FieldMask and support
# includedTypes with rectangle/circle locationRestriction; populartimes returns current_popularity
# when Google shows "Live" and weekly populartimes for historical fallback.

import math
import time
import requests
import populartimes
from typing import Optional, Dict, List, Tuple
from datetime import datetime


# Google Maps Platform API key (Places API enabled)
API_KEY = "AIzaSyA2h5N7d1EfTutMDw1r-O9Rh4J1JqoOYyM"

# Rutgers–New Brunswick center and rectangle radius (~7 km)
RUTGERS_CENTER_LAT = 40.50250
RUTGERS_CENTER_LNG = -74.44861
RUTGERS_RECT_RADIUS_M = 10000

# Places API v1 endpoints
PLACES_TEXTSEARCH_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
PLACES_NEARBY_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

# 1) Replace the SUBVENUE_TYPES list with v1-valid types (keep it small)
SUBVENUE_TYPES = [
    "restaurant",
    "cafe",
    "fast_food_restaurant",
    "food_court",
    "gym",
]  # v1 primary types suitable for nearby filtering



def _meter_to_lat_delta(meters: float) -> float:
    return meters / 111_320.0


def _meter_to_lng_delta(meters: float, at_lat: float) -> float:
    return meters / (111_320.0 * math.cos(math.radians(at_lat)))


def _rutgers_rectangle(radius_m: int) -> dict:
    dlat = _meter_to_lat_delta(radius_m)
    dlng = _meter_to_lng_delta(radius_m, RUTGERS_CENTER_LAT)
    return {
        "low": {"latitude": RUTGERS_CENTER_LAT - dlat, "longitude": RUTGERS_CENTER_LNG - dlng},
        "high": {"latitude": RUTGERS_CENTER_LAT + dlat, "longitude": RUTGERS_CENTER_LNG + dlng},
    }


def _fieldmask_header(mask: str) -> dict:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": mask,
    }


def _text_search_first(place_query: str, rect: dict, timeout_s: int = 30) -> Optional[Dict]:
    headers = _fieldmask_header("places.id,places.displayName,places.formattedAddress,places.location")
    body = {
        "textQuery": place_query,
        "pageSize": 5,
        "locationRestriction": {"rectangle": rect},
    }
    resp = requests.post(PLACES_TEXTSEARCH_ENDPOINT, headers=headers, json=body, timeout=timeout_s)
    resp.raise_for_status()
    data = resp.json()
    arr = data.get("places", [])
    return arr[0] if arr else None


# 2) Replace _nearby_places with a version that caps includedTypes to 5 and logs error details
def _nearby_places(lat: float, lng: float, radius_m: int, included_types: List[str], max_count: int = 20,
                   timeout_s: int = 30) -> List[Dict]:
    headers = _fieldmask_header("places.id,places.displayName,places.formattedAddress,places.location")  # v1 field mask
    body = {
        "maxResultCount": max(1, min(20, int(max_count))),  # v1 allows 1..20
        "includedTypes": included_types[:5],  # cap to 5 to avoid INVALID_ARGUMENT
        "locationRestriction": {
            "circle": {"center": {"latitude": float(lat), "longitude": float(lng)}, "radius": float(radius_m)}
        },
        # "rankPreference": "POPULARITY"  # optional; default is popularity
    }
    resp = requests.post(PLACES_NEARBY_ENDPOINT, headers=headers, json=body, timeout=timeout_s)
    if resp.status_code >= 400:
        try:
            # Print Google’s error to the console to aid debugging
            print("NearbySearch error:", resp.status_code, resp.text)
        except Exception:
            pass
        resp.raise_for_status()
    data = resp.json()
    return data.get("places", []) or []



def _hist_current_hour(info: dict) -> Optional[int]:
    pts = info.get("populartimes")
    if not isinstance(pts, list):
        return None
    weekday_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    now = datetime.now()
    dname = weekday_names[now.weekday()]
    hr = now.hour
    for d in pts:
        if d.get("name") == dname and isinstance(d.get("data"), list) and len(d["data"]) == 24:
            try:
                return int(d["data"][hr])
            except Exception:
                return None
    return None


def _get_popularity_for_id(place_id: str, delay_s: float = 0.2) -> Tuple[Optional[int], str, dict]:
    """
    Returns (value, source, raw) where:
      - value: 0..100 if available, else None
      - source: 'live' | 'historical' | 'unavailable'
      - raw: full populartimes payload
    """
    time.sleep(delay_s)
    info = populartimes.get_id(API_KEY, place_id)
    curr = info.get("current_popularity")
    if isinstance(curr, int):
        return curr, "live", info
    hist = _hist_current_hour(info)
    if isinstance(hist, int):
        return hist, "historical", info
    return None, "unavailable", info


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def _weighted_area_estimate(center_lat: float, center_lng: float, samples: List[Tuple[float,float,int]]) -> Optional[int]:
    """
    samples = [(lat, lng, popularity)]
    Weight by a Gaussian kernel over distance: w_i = exp(-(d_i^2)/(2*sigma^2)), sigma=150m
    """
    if not samples:
        return None
    sigma = 150.0
    num, den = 0.0, 0.0
    for lat, lng, val in samples:
        d = _haversine_m(center_lat, center_lng, lat, lng)
        w = math.exp(- (d*d) / (2.0 * sigma * sigma))
        num += w * val
        den += w
    if den <= 0:
        return None
    return int(round(num / den))


def resolve_and_measure(place_query: str) -> Optional[dict]:
    """
    Full flow for a Rutgers location:
      A) Resolve target place by name within Rutgers rectangle (Text Search v1)
      B) Try place's own popularity (live/historical)
      C) If unavailable, query sub-venues nearby and use best available
      D) If still unavailable, compute area-weighted estimate from multiple POIs
    Returns a dict with fields: name, address, coordinates, popularity, source, method, place_id.
    """
    rect = _rutgers_rectangle(RUTGERS_RECT_RADIUS_M)
    top = _text_search_first(place_query, rect)
    if not top:
        return None

    pid = top["id"]
    name = (top.get("displayName") or {}).get("text") or place_query
    addr = top.get("formattedAddress")
    loc = top.get("location") or {}
    clat, clng = loc.get("latitude"), loc.get("longitude")

    # Try the place itself
    val, src, raw = _get_popularity_for_id(pid)
    if isinstance(val, int):
        return {
            "place_id": pid,
            "name": name,
            "address": addr,
            "coordinates": {"lat": clat, "lng": clng},
            "popularity": val,
            "source": src,
            "method": "place",
        }

    # In resolve_and_measure(...) around the sub-venue and area calls
    try:
        sub_places = _nearby_places(clat, clng, radius_m=300, included_types=SUBVENUE_TYPES, max_count=20)
    except Exception:
        sub_places = []

    # ... later for area sampling:
    try:
        area_places = _nearby_places(clat, clng, radius_m=350, included_types=SUBVENUE_TYPES, max_count=20)
    except Exception:
        area_places = []

    # Sub-venues within 200m
    sub_places = _nearby_places(clat, clng, radius_m=300, included_types=SUBVENUE_TYPES, max_count=20)
    best = None
    for sp in sub_places:
        spid = sp.get("id")
        if not spid:
            continue
        sval, ssrc, sraw = _get_popularity_for_id(spid)
        if isinstance(sval, int):
            sname = (sp.get("displayName") or {}).get("text")
            sloc = sp.get("location") or {}
            slat, slng = sloc.get("latitude"), sloc.get("longitude")
            # Prefer any live; otherwise highest historical
            rank = (2 if ssrc == "live" else 1, sval)
            if best is None or rank > best["rank"]:
                best = {
                    "val": sval, "src": ssrc, "id": spid, "name": sname,
                    "lat": slat, "lng": slng, "rank": rank
                }
    if best:
        return {
            "place_id": pid,
            "name": name,
            "address": addr,
            "coordinates": {"lat": clat, "lng": clng},
            "popularity": best["val"],
            "source": best["src"],
            "method": "subvenue",
            "subvenue": {"id": best["id"], "name": best["name"], "lat": best["lat"], "lng": best["lng"]},
        }

    # Area estimate from up to 20 nearby POIs within 250m
    area_places = _nearby_places(clat, clng, radius_m=300, included_types=SUBVENUE_TYPES, max_count=20)
    samples = []
    for ap in area_places:
        apid = ap.get("id")
        if not apid:
            continue
        aval, asrc, araw = _get_popularity_for_id(apid)
        if isinstance(aval, int):
            aloc = ap.get("location") or {}
            alat, alng = aloc.get("latitude"), aloc.get("longitude")
            if isinstance(alat, float) and isinstance(alng, float):
                samples.append((alat, alng, aval))
    est = _weighted_area_estimate(clat, clng, samples)
    if isinstance(est, int):
        return {
            "place_id": pid,
            "name": name,
            "address": addr,
            "coordinates": {"lat": clat, "lng": clng},
            "popularity": est,
            "source": "area",
            "method": "area_weighted",
            "samples_used": len(samples),
        }

    # Nothing available
    return {
        "place_id": pid,
        "name": name,
        "address": addr,
        "coordinates": {"lat": clat, "lng": clng},
        "popularity": None,
        "source": "unavailable",
        "method": "none",
    }


if __name__ == "__main__":
    # Example manual check
    q = "College Ave Student Center"
    out = resolve_and_measure(q)
    print(out)

    # ====== Additions for time-aware, compact answers ======
import re
from datetime import timedelta

def _hist_at(info: dict, when_local) -> Optional[int]:
    """Historical Popular Times value for the given local datetime's weekday/hour."""
    pts = info.get("populartimes")
    if not isinstance(pts, list):
        return None
    weekday_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    target_day = weekday_names[when_local.weekday()]
    target_hour = when_local.hour
    for d in pts:
        if d.get("name") == target_day and isinstance(d.get("data"), list) and len(d["data"]) == 24:
            try:
                return int(d["data"][target_hour])
            except Exception:
                return None
    return None

def _hist_around(info: dict, when_local, window_hours: int = 1) -> Optional[int]:
    """Average historical Popular Times over +/- window_hours from target hour."""
    vals = []
    base = when_local.replace(minute=0, second=0, microsecond=0)
    for off in range(-window_hours, window_hours+1):
        dt = base + timedelta(hours=off)
        v = _hist_at(info, dt)
        if isinstance(v, int):
            vals.append(v)
    if not vals:
        return None
    return int(round(sum(vals) / len(vals)))

def _get_popularity_for_id_at(place_id: str, when_local, allow_live: bool, delay_s: float = 0.2):
    """
    Returns (value, source, raw) at a specific time:
      - if allow_live and Google exposes live now: ('live', current_popularity)
      - else historical at the requested hour (or +/-1h avg) if available
      - else unavailable
    """
    time.sleep(delay_s)
    info = populartimes.get_id(API_KEY, place_id)
    # Live only makes sense if querying "now"
    if allow_live:
        curr = info.get("current_popularity")
        if isinstance(curr, int):
            return curr, "live", info
    # Historical at requested time (use +/-1h smoothing)
    hist = _hist_around(info, when_local, window_hours=1)
    if isinstance(hist, int):
        return hist, "historical", info
    return None, "unavailable", info

def _is_now(when_local) -> bool:
    now = datetime.now()
    return abs((when_local - now).total_seconds()) <= 30 * 60  # within 30 minutes counts as "now"

def _normalize_place_query(q: str) -> str:
    s = q.lower()
    if "busch" in s:
        return "Busch Student Center Rutgers"
    if "college ave" in s or "college avenue" in s or "cac" in s:
        return "College Ave Student Center Rutgers"
    if "livingston" in s or "livi" in s:
        return "Livingston Student Center Rutgers"
    if "cook" in s:
        return "Cook Student Center Rutgers"
    if "douglass" in s or "doug" in s:
        return "Douglass Student Center Rutgers"
    return q

def _parse_when(q: str):
    """
    Parse phrases like 'around 7pm today', 'at 19:00', '7 pm', 'now'.
    Defaults to 'now' if no time words found.
    """
    now = datetime.now()
    s = q.lower()
    if "now" in s:
        return now
    # day hint
    day_offset = 0
    if "tomorrow" in s:
        day_offset = 1
    elif "today" in s:
        day_offset = 0
    # time
    m = re.search(r"(?:at|around)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", s)
    if not m:
        return now
    hh = int(m.group(1))
    mm = int(m.group(2) or "0")
    ap = m.group(3)
    if ap == "pm" and hh < 12:
        hh += 12
    if ap == "am" and hh == 12:
        hh = 0
    dt = now.replace(hour=min(max(hh,0),23), minute=min(max(mm,0),59), second=0, microsecond=0) + timedelta(days=day_offset)
    return dt

def resolve_and_measure_at(place_query: str, when_local) -> Optional[dict]:
    """
    Same as resolve_and_measure, but time-aware:
      - if when_local ~ now: try live; else fetch historical for that hour
      - sub-venue and area fallbacks also use the requested time
    """
    rect = _rutgers_rectangle(RUTGERS_RECT_RADIUS_M)
    top = _text_search_first(place_query, rect)
    if not top:
        return None

    pid = top["id"]
    name = (top.get("displayName") or {}).get("text") or place_query
    addr = top.get("formattedAddress")
    loc = top.get("location") or {}
    clat, clng = loc.get("latitude"), loc.get("longitude")

    allow_live = _is_now(when_local)

    # A) Place itself
    val, src, raw = _get_popularity_for_id_at(pid, when_local, allow_live=allow_live)
    if isinstance(val, int):
        return {
            "place_id": pid,
            "name": name,
            "address": addr,
            "coordinates": {"lat": clat, "lng": clng},
            "popularity": val,
            "source": src,
            "method": "place",
            "when": when_local.isoformat()
        }

    # B) Sub-venues (200m)
    try:
        sub_places = _nearby_places(clat, clng, radius_m=300, included_types=SUBVENUE_TYPES, max_count=15)
    except Exception:
        sub_places = []
    best = None
    for sp in sub_places:
        spid = sp.get("id")
        if not spid: 
            continue
        sval, ssrc, _ = _get_popularity_for_id_at(spid, when_local, allow_live=allow_live)
        if isinstance(sval, int):
            # Prefer live over historical, then higher value
            rank = (2 if ssrc == "live" else 1, sval)
            if not best or rank > best["rank"]:
                sloc = sp.get("location") or {}
                best = {
                    "val": sval, "src": ssrc, "rank": rank,
                    "id": spid, "name": (sp.get("displayName") or {}).get("text"),
                    "lat": sloc.get("latitude"), "lng": sloc.get("longitude")
                }
    if best:
        return {
            "place_id": pid,
            "name": name,
            "address": addr,
            "coordinates": {"lat": clat, "lng": clng},
            "popularity": best["val"],
            "source": best["src"],
            "method": "subvenue",
            "subvenue": {"id": best["id"], "name": best["name"], "lat": best["lat"], "lng": best["lng"]},
            "when": when_local.isoformat()
        }

    # C) Area estimate (250m)
    try:
        area_places = _nearby_places(clat, clng, radius_m=300, included_types=SUBVENUE_TYPES, max_count=15)
    except Exception:
        area_places = []
    samples = []
    for ap in area_places:
        apid = ap.get("id")
        if not apid:
            continue
        aval, asrc, _ = _get_popularity_for_id_at(apid, when_local, allow_live=allow_live)
        if isinstance(aval, int):
            aloc = ap.get("location") or {}
            alat, alng = aloc.get("latitude"), aloc.get("longitude")
            if isinstance(alat, float) and isinstance(alng, float):
                samples.append((alat, alng, aval))
    est = _weighted_area_estimate(clat, clng, samples)
    if isinstance(est, int):
        return {
            "place_id": pid,
            "name": name,
            "address": addr,
            "coordinates": {"lat": clat, "lng": clng},
            "popularity": est,
            "source": "area",
            "method": "area_weighted",
            "samples_used": len(samples),
            "when": when_local.isoformat()
        }

    return {
        "place_id": pid,
        "name": name,
        "address": addr,
        "coordinates": {"lat": clat, "lng": clng},
        "popularity": None,
        "source": "unavailable",
        "method": "none",
        "when": when_local.isoformat()
    }

def compact_answer(query_text: str) -> str:
    """
    Parse 'how crowded is busch around 7pm today' and return 'NN% 🟡 medium'.
    """
    when = _parse_when(query_text)
    target = _normalize_place_query(query_text)
    r = resolve_and_measure_at(target, when)
    val = r and r.get("popularity")
    if val is None:
        return "unavailable ⚪ unknown"
    if val < 30:
        return f"{val}% 🟢 light"
    if val < 60:
        return f"{val}% 🟡 medium"
    if val < 85:
        return f"{val}% 🟠 high"
    return f"{val}% 🔴 red"
# ====== End additions ======

