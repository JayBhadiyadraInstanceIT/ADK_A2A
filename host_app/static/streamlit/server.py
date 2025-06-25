# server.py
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio
import base64
import json

app = FastAPI()
queues = {}

@app.post("/send/{session_id}")
async def send(session_id: str, req: Request):
    msg = await req.json()
    q = queues.get(session_id)
    if not q:
        return JSONResponse(status_code=404, content={"error": "No session"})
    await q.put(msg)
    return {"status": "ok"}

@app.get("/events/{session_id}")
async def events(session_id: str, is_audio: bool = False):
    q = asyncio.Queue()
    queues[session_id] = q

    async def streamer():
        try:
            while True:
                msg = await q.get()
                payload = f"data: {json.dumps(msg)}\n\n"
                yield payload
        except asyncio.CancelledError:
            pass
        finally:
            queues.pop(session_id, None)

    return StreamingResponse(streamer(), media_type="text/event-stream")
