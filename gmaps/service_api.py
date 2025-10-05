# service_api.py
# FastAPI wrapper exposing GET /busyness?q=... to return JSON for the bot/app.

import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from rutgers_busyness import resolve_and_measure

app = FastAPI(title="Rutgers Busyness API")

@app.get("/busyness")
def busyness(q: str = Query(..., description="Place name, e.g., 'College Ave Student Center'")):
    data = resolve_and_measure(q)
    if not data:
        return JSONResponse({"query": q, "error": "not_found"}, status_code=404)
    return {"query": q, "result": data}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
