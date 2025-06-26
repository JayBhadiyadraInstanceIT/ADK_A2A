import os
import json
import base64
import warnings
import asyncio
import traceback
import subprocess
import time
import socket
import uvicorn

from pathlib import Path
from dotenv import load_dotenv

from google.genai.types import (
    Part,
    Content,
    Blob,
)
from google.genai import types

from google.adk.runners import InMemoryRunner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import the enhanced multimodal host agent
from host_agent import root_agent


class Message(BaseModel):
    mime_type: str
    data: str


warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

#
# ADK Streaming with Enhanced Multimodal Host Agent
#

# Load Gemini API Key
load_dotenv()

APP_NAME = "Pickleball Scheduling Agent"


async def start_agent_session(user_id, is_audio=False):
    """Starts an enhanced agent session with pickleball scheduling capabilities"""

    # Create a Runner with the multimodal host agent
    runner = InMemoryRunner(
        app_name=APP_NAME,
        agent=root_agent,
    )

    # Create a Session
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
    )

    # Set response modality
    modality = "AUDIO" if is_audio else "TEXT"

    # Enhanced speech configuration for better pickleball scheduling conversations
    speech_config = types.SpeechConfig(
        voice_config=types.VoiceConfig(
            # Use a friendly, clear voice for scheduling conversations
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede") # Voice Change by name you want to 
        )
    )

    config = {"response_modalities": [modality]}
    
    # Only add speech config if audio is enabled
    if is_audio:
        config["speech_config"] = speech_config
        config["output_audio_transcription"] = {}

    run_config = RunConfig(**config)

    # Create a LiveRequestQueue for this session
    live_request_queue = LiveRequestQueue()

    # Start agent session
    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    return live_events, live_request_queue


async def agent_to_client_sse(live_events):
    """Enhanced agent to client communication via SSE with scheduling updates"""
    try:
        async for event in live_events:
            try:
                # If the turn complete or interrupted, send it
                if event.turn_complete or event.interrupted:
                    message = {
                        "turn_complete": event.turn_complete,
                        "interrupted": event.interrupted,
                    }
                    yield f"data: {json.dumps(message)}\n\n"
                    print(f"[AGENT TO CLIENT]: {message}")
                    continue

                # Read the Content and its first Part
                part: Part = (
                    event.content and event.content.parts and event.content.parts[0]
                )
                if not part:
                    continue

                # If it's audio, send Base64 encoded audio data
                is_audio = part.inline_data and part.inline_data.mime_type.startswith("audio/pcm")
                if is_audio:
                    audio_data = part.inline_data and part.inline_data.data
                    if audio_data:
                        message = {
                            "mime_type": "audio/pcm",
                            "data": base64.b64encode(audio_data).decode("ascii")
                        }
                        yield f"data: {json.dumps(message)}\n\n"
                        print(f"[AGENT TO CLIENT]: audio/pcm: {len(audio_data)} bytes.")
                        continue

                # If it's text and a partial text, send it
                if part.text and event.partial:
                    message = {
                        "mime_type": "text/plain",
                        "data": part.text
                    }
                    yield f"data: {json.dumps(message)}\n\n"
                    print(f"[AGENT TO CLIENT]: text/plain: {message}")
                    
            except Exception as e:
                print(f"Error processing event: {e}")
                traceback.print_exc()
                continue
                
    except Exception as e:
        print(f"Error in agent_to_client_sse: {e}")
        traceback.print_exc()
        # Send error message to client
        error_message = {
            "error": "Stream interrupted",
            "details": str(e)
        }
        yield f"data: {json.dumps(error_message)}\n\n"


#
# Enhanced FastAPI web app for Pickleball Scheduling
#

app = FastAPI(
    title="Multimodal Pickleball Scheduling Agent",
    description="An AI agent that can schedule pickleball games with friends using both text and voice interactions"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# STATIC_DIR = Path("static")
# app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Store active sessions
active_sessions = {}
queues = {}


# @app.get("/")
# async def root():
#     """Serves the enhanced index.html for pickleball scheduling"""
#     return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/")
async def redirect_to_streamlit():
    """Serves the enhanced streamlit UI for pickleball scheduling"""
    return RedirectResponse("http://localhost:8501")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "pickleball_host"}


@app.get("/events/{user_id}")
async def sse_endpoint(user_id: int, is_audio: str = "false"):
    """Enhanced SSE endpoint for multimodal agent to client communication"""

    user_id_str = str(user_id)
    
    try:
        # Start agent session
        live_events, live_request_queue = await start_agent_session(user_id_str, is_audio == "true")

        # Store the request queue for this user
        active_sessions[user_id_str] = live_request_queue

        print(f"Pickleball Scheduling Client #{user_id} connected via SSE, audio mode: {is_audio}")

        def cleanup():
            try:
                live_request_queue.close()
                if user_id_str in active_sessions:
                    del active_sessions[user_id_str]
                print(f"Pickleball Scheduling Client #{user_id} disconnected from SSE")
            except Exception as e:
                print(f"Error during cleanup: {e}")

        async def event_generator():
            try:
                async for data in agent_to_client_sse(live_events):
                    yield data
            except Exception as e:
                print(f"Error in SSE stream: {e}")
                traceback.print_exc()
                # Send error to client before closing
                error_message = {
                    "error": "Connection lost",
                    "message": "Please refresh the page to reconnect"
                }
                yield f"data: {json.dumps(error_message)}\n\n"
            finally:
                cleanup()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except Exception as e:
        print(f"Error starting SSE session: {e}")
        traceback.print_exc()
        return {"error": f"Failed to start session: {str(e)}"}


@app.post("/send/{user_id}")
async def send_message_endpoint(user_id: int, request: Request):
    """Enhanced HTTP endpoint for client to multimodal agent communication"""

    user_id_str = str(user_id)

    try:
        # Get the live request queue for this user
        live_request_queue = active_sessions.get(user_id_str)
        if not live_request_queue:
            return {"error": "Session not found"}

        # Parse the message
        message = await request.json()
        mime_type = message["mime_type"]
        data = message["data"]

        # Send the message to the agent
        if mime_type == "text/plain":
            content = Content(role="user", parts=[Part.from_text(text=data)])
            live_request_queue.send_content(content=content)
            print(f"[CLIENT TO AGENT]: {data}")
        elif mime_type == "audio/pcm":
            decoded_data = base64.b64decode(data)
            live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
            print(f"[CLIENT TO AGENT]: audio/pcm: {len(decoded_data)} bytes")
        else:
            return {"error": f"Mime type not supported: {mime_type}"}

        return {"status": "sent"}
        
    except Exception as e:
        print(f"Error sending message: {e}")
        traceback.print_exc()
        return {"error": f"Failed to send message: {str(e)}"}


@app.get("/agents/status")
async def get_agent_status():
    """Get the status of connected friend agents"""
    try:
        # This would ideally check the actual agent connections
        # For now, return a basic status
        return {
            "host_agent": "host_agent",
            "capabilities": ["text", "audio", "pickleball_scheduling", "google_search"],
            "active_sessions": len(active_sessions),
            "remote_agents": ["Karley_Agent", "Nate_Agent", "Kaitlynn_Agent"]
        }
    except Exception as e:
        print(f"Error getting agent status: {e}")
        return {"error": str(e)}


@app.get("/debug/sessions")
async def debug_sessions():
    """Debug endpoint to check active sessions"""
    return {
        "active_sessions": list(active_sessions.keys()),
        "session_count": len(active_sessions)
    }


@app.post("/send/{session_id}")
async def send(session_id: str, msg: Message):
    q = queues.setdefault(session_id, asyncio.Queue())
    await q.put({
        "mime_type": msg.mime_type,
        "data": msg.data
    })
    return {"status": "ok"}


@app.get("/events/{session_id}")
async def stream_events(session_id: str, request: Request):
    async def event_generator():
        q = queues.setdefault(session_id, asyncio.Queue())

        while True:
            # Disconnect if client closes connection
            if await request.is_disconnected():
                break

            try:
                msg = await asyncio.wait_for(q.get(), timeout=15)
                yield f"data: {json.dumps(msg)}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def wait_for_port(host, port, timeout=15):
    """Wait until a port starts accepting TCP connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


# Development server startup
if __name__ == "__main__":
    # Auto-launch Streamlit UI
    # frontend_path = os.path.join("static", "streamlit", "app.py")
    # subprocess.Popen(["streamlit", "run", frontend_path])

    # time.sleep(2)

    # Launch FastAPI
    # uvicorn.run(
    #     "main:app", 
    #     host="localhost", # 0.0.0.0
    #     port=7000, 
    #     reload=True,
    #     log_level="info"
    # )

    # Start FastAPI (main app) in a subprocess
    proc = subprocess.Popen([
        "uvicorn", "main:app", 
        "--host", "localhost", 
        "--port", "7000", 
        "--reload",
    ])
    print("🚀 FastAPI launched, waiting for readiness...")

    # Wait until FastAPI server is up
    if wait_for_port("localhost", 7000):
        print("✅ FastAPI is ready. Launching Streamlit...")

        # Launch Streamlit as a separate subprocess
        streamlit_proc = subprocess.Popen([
            "streamlit", "run", "static/streamlit/app.py"
        ])
        print("🎉 Streamlit launched at http://localhost:8501")

    else:
        print("❌ FastAPI did not start in time.")
