# # Copyright 2025 Google LLC
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# #     http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.

# import os
# import json
# import base64
# import warnings

# from pathlib import Path
# from dotenv import load_dotenv

# from google.genai.types import (
#     Part,
#     Content,
#     Blob,
# )
# from google.genai import types

# from google.adk.runners import InMemoryRunner
# from google.adk.agents import LiveRequestQueue
# from google.adk.agents.run_config import RunConfig

# from fastapi import FastAPI, Request
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import FileResponse, StreamingResponse
# from fastapi.middleware.cors import CORSMiddleware

# from host_agent.agent import root_agent

# warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# #
# # ADK Streaming
# #

# # Load Gemini API Key
# load_dotenv()

# APP_NAME = "ADK Streaming example"


# async def start_agent_session(user_id, is_audio=False):
#     """Starts an agent session"""

#     # Create a Runner
#     runner = InMemoryRunner(
#         app_name=APP_NAME,
#         agent=root_agent,
#     )

#     # Create a Session
#     session = await runner.session_service.create_session(
#         app_name=APP_NAME,
#         user_id=user_id,  # Replace with actual user ID
#     )

#     # Set response modality
#     modality = "AUDIO" if is_audio else "TEXT"

#     speech_config = types.SpeechConfig(
#         voice_config=types.VoiceConfig(
#             # Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, and Zephyr
#             prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
#         )
#     )

#     config = {"response_modalities": [modality], "speech_config": speech_config}

#     # Add output_audio_transcription when audio is enabled to get both audio and text
#     if is_audio:
#         config["output_audio_transcription"] = {}

#     run_config = RunConfig(**config)

#     # run_config = RunConfig(response_modalities=[modality])

#     # Create a LiveRequestQueue for this session
#     live_request_queue = LiveRequestQueue()

#     # Start agent session
#     live_events = runner.run_live(
#         session=session,
#         live_request_queue=live_request_queue,
#         run_config=run_config,
#     )
#     return live_events, live_request_queue


# async def agent_to_client_sse(live_events):
#     """Agent to client communication via SSE"""
#     async for event in live_events:
#         # If the turn complete or interrupted, send it
#         if event.turn_complete or event.interrupted:
#             message = {
#                 "turn_complete": event.turn_complete,
#                 "interrupted": event.interrupted,
#             }
#             yield f"data: {json.dumps(message)}\n\n"
#             print(f"[AGENT TO CLIENT]: {message}")
#             continue

#         # Read the Content and its first Part
#         part: Part = (
#             event.content and event.content.parts and event.content.parts[0]
#         )
#         if not part:
#             continue

#         # If it's audio, send Base64 encoded audio data
#         is_audio = part.inline_data and part.inline_data.mime_type.startswith("audio/pcm")
#         if is_audio:
#             audio_data = part.inline_data and part.inline_data.data
#             if audio_data:
#                 message = {
#                     "mime_type": "audio/pcm",
#                     "data": base64.b64encode(audio_data).decode("ascii")
#                 }
#                 yield f"data: {json.dumps(message)}\n\n"
#                 print(f"[AGENT TO CLIENT]: audio/pcm: {len(audio_data)} bytes.")
#                 continue

#         # If it's text and a parial text, send it
#         if part.text and event.partial:
#             message = {
#                 "mime_type": "text/plain",
#                 "data": part.text
#             }
#             yield f"data: {json.dumps(message)}\n\n"
#             print(f"[AGENT TO CLIENT]: text/plain: {message}")


# #
# # FastAPI web app
# #

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # STATIC_DIR = Path("static")

# BASE_DIR = Path(__file__).resolve().parent
# STATIC_DIR = BASE_DIR / "static"

# app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# # Store active sessions
# active_sessions = {}


# @app.get("/")
# async def root():
#     """Serves the index.html"""
#     return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# @app.get("/events/{user_id}")
# async def sse_endpoint(user_id: int, is_audio: str = "false"):
#     """SSE endpoint for agent to client communication"""

#     # Start agent session
#     user_id_str = str(user_id)
#     live_events, live_request_queue = await start_agent_session(user_id_str, is_audio == "true")

#     # Store the request queue for this user
#     active_sessions[user_id_str] = live_request_queue

#     print(f"Client #{user_id} connected via SSE, audio mode: {is_audio}")

#     def cleanup():
#         live_request_queue.close()
#         if user_id_str in active_sessions:
#             del active_sessions[user_id_str]
#         print(f"Client #{user_id} disconnected from SSE")

#     async def event_generator():
#         try:
#             async for data in agent_to_client_sse(live_events):
#                 yield data
#         except Exception as e:
#             print(f"Error in SSE stream: {e}")
#         finally:
#             cleanup()

#     return StreamingResponse(
#         event_generator(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "Access-Control-Allow-Origin": "*",
#             "Access-Control-Allow-Headers": "Cache-Control"
#         }
#     )


# @app.post("/send/{user_id}")
# async def send_message_endpoint(user_id: int, request: Request):
#     """HTTP endpoint for client to agent communication"""

#     user_id_str = str(user_id)

#     # Get the live request queue for this user
#     live_request_queue = active_sessions.get(user_id_str)
#     if not live_request_queue:
#         return {"error": "Session not found"}

#     # Parse the message
#     message = await request.json()
#     mime_type = message["mime_type"]
#     data = message["data"]

#     # Send the message to the agent
#     if mime_type == "text/plain":
#         content = Content(role="user", parts=[Part.from_text(text=data)])
#         live_request_queue.send_content(content=content)
#         print(f"[CLIENT TO AGENT]: {data}")
#     elif mime_type == "audio/pcm":
#         decoded_data = base64.b64decode(data)
#         live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
#         print(f"[CLIENT TO AGENT]: audio/pcm: {len(decoded_data)} bytes")
#     else:
#         return {"error": f"Mime type not supported: {mime_type}"}

#     return {"status": "sent"}

#======================================================================================================================================================
# app/main.py
# import asyncio
# _original_create_connection = asyncio.BaseEventLoop.create_connection
# def _patched_create_connection(self, *args, **kwargs):
#     kwargs.pop("extra_headers", None)
#     return _original_create_connection(self, *args, **kwargs)
# asyncio.BaseEventLoop.create_connection = _patched_create_connection
# import os
# import json
# import base64
# import uuid
# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import FileResponse
# from pathlib import Path

# from google.adk.runners import InMemoryRunner
# from google.genai import types
# from google.adk.agents import LiveRequestQueue
# from google.genai.types import (
#     Part,
#     Content,
#     Blob,
# )
# from fastapi.staticfiles import StaticFiles
# from google.adk.agents.run_config import RunConfig
# from fastapi.responses import StreamingResponse


# from host_agent.agent import root_agent

# app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Use absolute path for static files directory
# # STATIC_DIR = Path(__file__).parent / "static"
# STATIC_DIR = Path("static")

# app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# active_sessions = {}

# @app.get("/")
# async def root():
#     """Serves the static index.html UI."""
#     return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# # @app.get("/events/{user_id}")
# # async def sse_endpoint(user_id: int, is_audio: str = "false"):
# #     """Server-Sent Events endpoint for streaming agent responses to the client."""
# #     # Start a new agent session
# #     user_id_str = str(user_id)
# #     live_events, live_request_queue = await start_agent_session(user_id_str, is_audio == "true")
# #     # Store the queue so /send/ can access it
# #     active_sessions[user_id_str] = live_request_queue
# #     print(f"Client #{user_id} connected via SSE (audio mode: {is_audio}).")
# #     # Clean-up callback when client disconnects
# #     def cleanup():
# #         live_request_queue.close()
# #         active_sessions.pop(user_id_str, None)
# #         print(f"Client #{user_id} session ended.")
# #     # Return a streaming response
# #     return types.ServerSentEventResponse(live_events, on_close=cleanup)


# @app.get("/events/{user_id}")
# async def sse_endpoint(user_id: int, is_audio: str = "false"):
#     """Server-Sent Events endpoint for streaming agent responses to the client."""
#     # Start a new agent session
#     user_id_str = str(user_id)
#     live_events, live_request_queue = await start_agent_session(user_id_str, is_audio == "true")
#     # Store the queue so /send/ can access it
#     active_sessions[user_id_str] = live_request_queue
#     print(f"Client #{user_id} connected via SSE (audio mode: {is_audio}).")

#     def cleanup():
#         live_request_queue.close()
#         active_sessions.pop(user_id_str, None)
#         print(f"Client #{user_id} session ended.")

#     async def agent_to_client_sse():
#         try:
#             async for event in live_events:
#                 # Turn complete or interrupted
#                 if event.turn_complete or event.interrupted:
#                     yield f"data: {json.dumps({'turn_complete': event.turn_complete, 'interrupted': event.interrupted})}\n\n"
#                     continue

#                 part: Part = event.content.parts[0] if event.content and event.content.parts else None
#                 if not part:
#                     continue

#                 if part.text and event.partial:
#                     msg = part.text
#                     print(f"[CLIENT] Agent: {msg}")
#                     yield f"data: {json.dumps({'mime_type': 'text/plain', 'data': part.text})}\n\n"

#                 if part.inline_data and part.inline_data.mime_type.startswith("audio/pcm"):
#                     encoded = base64.b64encode(part.inline_data.data).decode("ascii")
#                     yield f"data: {json.dumps({'mime_type': 'audio/pcm', 'data': encoded})}\n\n"
#         except Exception as e:
#             print(f"Streaming error: {e}")
#         finally:
#             cleanup()

#     return StreamingResponse(
#         agent_to_client_sse(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "Access-Control-Allow-Origin": "*"
#         }
#     )


# @app.post("/send/{user_id}")
# async def send_message_endpoint(user_id: int, request: Request):
#     """Endpoint for client to send text or audio input to the agent."""
#     user_id_str = str(user_id)
#     live_request_queue = active_sessions.get(user_id_str)
#     if not live_request_queue:
#         return {"error": "Session not found"}

#     message = await request.json()
#     mime_type = message.get("mime_type")
#     data = message.get("data")

#     # Send the content (text or audio) into the agent session
#     if mime_type == "text/plain":
#         content = Content(role="user", parts=[Part.from_text(text=data)])
#         live_request_queue.send_content(content=content)
#         print(f"[CLIENT] User: {data}")
#     elif mime_type == "audio/pcm":
#         decoded_data = base64.b64decode(data)
#         live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
#         print(f"[CLIENT] Sent audio ({len(decoded_data)} bytes).")
#     else:
#         return {"error": f"Mime type not supported: {mime_type}"}

#     return {"status": "sent"}


# # --- Agent session management ---
# from google.genai import types as genai_types
# APP_NAME = "PickleballSchedulingApp"
# active_sessions: dict[str, LiveRequestQueue] = {}

# async def start_agent_session(user_id: str, is_audio: bool):
#     """Starts a new conversation session with the Host agent."""
#     # Create a runner with the Host agent
#     runner = InMemoryRunner(app_name=APP_NAME, agent=root_agent)
#     # Create a new session for this user
#     session = await runner.session_service.create_session(
#         app_name=APP_NAME,
#         user_id=user_id,
#     )
#     # Configure modalities (text and/or audio)
#     modalities = []
#     # if is_audio:
#     #     # modalities.append(types.OutputModality.AUDIO)
#     #     modalities.append("audio")
#     #     # modalities.append(types.OutputModality.TEXT)
#     #     modalities.append("text")
#     # else:
#     #     # modalities.append(types.OutputModality.TEXT)
#     #     modalities.append("text")
#     # # run_config = types.RunConfig(response_modalities=modalities)
#     # run_config = RunConfig(response_modalities=modalities)
#     # # Start the live agent loop
#     # live_request_queue = LiveRequestQueue()
#     # live_events = runner.run_live(
#     #     session=session,
#     #     live_request_queue=live_request_queue,
#     #     run_config=run_config,
#     # )
#     # return live_events, live_request_queue

#     if is_audio:
#         speech_config = genai_types.SpeechConfig(
#             voice_config=genai_types.VoiceConfig(
#                 prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name="Aoede")
#             )
#         )
#         run_config = RunConfig(
#             response_modalities=["AUDIO"],
#             speech_config=speech_config,
#             output_audio_transcription={},  # optional transcription
#         )
#     else:
#         run_config = RunConfig(response_modalities=["TEXT"])

#     live_request_queue = LiveRequestQueue()
#     live_events = runner.run_live(
#         session=session,
#         live_request_queue=live_request_queue,
#         run_config=run_config,
#     )

#     return live_events, live_request_queue
#======================================================================================================================================================
# import os
# import json
# import base64
# import uuid
# import asyncio
# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import FileResponse
# from pathlib import Path

# from google.adk.runners import InMemoryRunner
# from google.genai import types
# from google.adk.agents import LiveRequestQueue
# from google.genai.types import (
#     Part,
#     Content,
#     Blob,
# )
# from fastapi.staticfiles import StaticFiles
# from google.adk.agents.run_config import RunConfig
# from fastapi.responses import StreamingResponse

# from host_agent.agent import root_agent

# app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Use absolute path for static files directory
# STATIC_DIR = Path("static")
# app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# active_sessions = {}

# @app.get("/")
# async def root():
#     """Serves the static index.html UI."""
#     return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# @app.get("/events/{user_id}")
# async def sse_endpoint(user_id: int, is_audio: str = "false"):
#     """Server-Sent Events endpoint for streaming agent responses to the client."""
#     user_id_str = str(user_id)
    
#     # Clean up any existing session for this user
#     if user_id_str in active_sessions:
#         try:
#             active_sessions[user_id_str].close()
#         except Exception as e:
#             print(f"Error closing existing session: {e}")
#         finally:
#             active_sessions.pop(user_id_str, None)
    
#     try:
#         live_events, live_request_queue = await start_agent_session(user_id_str, is_audio == "true")
#         active_sessions[user_id_str] = live_request_queue
#         print(f"Client #{user_id} connected via SSE (audio mode: {is_audio}).")
#     except Exception as e:
#         print(f"Error starting agent session: {e}")
#         return {"error": "Failed to start session"}

#     def cleanup():
#         try:
#             if user_id_str in active_sessions:
#                 active_sessions[user_id_str].close()
#                 active_sessions.pop(user_id_str, None)
#         except Exception as e:
#             print(f"Error during cleanup: {e}")
#         print(f"Client #{user_id} session ended.")

#     async def agent_to_client_sse():
#         try:
#             async for event in live_events:
#                 try:
#                     # Handle turn completion or interruption
#                     if hasattr(event, 'turn_complete') and (event.turn_complete or getattr(event, 'interrupted', False)):
#                         yield f"data: {json.dumps({'turn_complete': event.turn_complete, 'interrupted': getattr(event, 'interrupted', False)})}\n\n"
#                         continue

#                     # Handle content events
#                     if hasattr(event, 'content') and event.content and event.content.parts:
#                         part: Part = event.content.parts[0]
                        
#                         # Handle text content
#                         if hasattr(part, 'text') and part.text and getattr(event, 'partial', False):
#                             msg = part.text
#                             print(f"[CLIENT] Agent: {msg}")
#                             yield f"data: {json.dumps({'mime_type': 'text/plain', 'data': part.text})}\n\n"

#                         # Handle audio content
#                         if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.mime_type.startswith("audio/pcm"):
#                             encoded = base64.b64encode(part.inline_data.data).decode("ascii")
#                             yield f"data: {json.dumps({'mime_type': 'audio/pcm', 'data': encoded})}\n\n"

#                 except Exception as event_error:
#                     print(f"Error processing event: {event_error}")
#                     continue

#         except asyncio.CancelledError:
#             print(f"SSE stream cancelled for client #{user_id}")
#         except Exception as e:
#             print(f"Streaming error: {e}")
#         finally:
#             cleanup()

#     return StreamingResponse(
#         agent_to_client_sse(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "Access-Control-Allow-Origin": "*",
#             "X-Accel-Buffering": "no"  # Disable nginx buffering if using nginx
#         }
#     )

# @app.post("/send/{user_id}")
# async def send_message_endpoint(user_id: int, request: Request):
#     """Endpoint for client to send text or audio input to the agent."""
#     user_id_str = str(user_id)
#     live_request_queue = active_sessions.get(user_id_str)
    
#     if not live_request_queue:
#         return {"error": "Session not found. Please reconnect."}

#     try:
#         message = await request.json()
#         mime_type = message.get("mime_type")
#         data = message.get("data")

#         if not mime_type or not data:
#             return {"error": "Missing mime_type or data"}

#         # Send the content (text or audio) into the agent session
#         if mime_type == "text/plain":
#             content = Content(role="user", parts=[Part.from_text(text=data)])
#             live_request_queue.send_content(content=content)
#             print(f"[CLIENT] User: {data}")
#         elif mime_type == "audio/pcm":
#             try:
#                 decoded_data = base64.b64decode(data)
#                 live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
#                 print(f"[CLIENT] Sent audio ({len(decoded_data)} bytes).")
#             except Exception as audio_error:
#                 print(f"Error processing audio: {audio_error}")
#                 return {"error": "Failed to process audio data"}
#         else:
#             return {"error": f"Mime type not supported: {mime_type}"}

#         return {"status": "sent"}
    
#     except Exception as e:
#         print(f"Error in send_message_endpoint: {e}")
#         return {"error": "Failed to process message"}

# # --- Agent session management ---
# from google.genai import types as genai_types

# APP_NAME = "PickleballSchedulingApp"

# async def start_agent_session(user_id: str, is_audio: bool):
#     """Starts a new conversation session with the Host agent."""
#     try:
#         # Create a runner with the Host agent
#         runner = InMemoryRunner(app_name=APP_NAME, agent=root_agent)
        
#         # Create a new session for this user
#         session = await runner.session_service.create_session(
#             app_name=APP_NAME,
#             user_id=user_id,
#         )
        
#         # Configure modalities (text and/or audio)
#         if is_audio:
#             speech_config = genai_types.SpeechConfig(
#                 voice_config=genai_types.VoiceConfig(
#                     prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name="Aoede")
#                 )
#             )
#             run_config = RunConfig(
#                 response_modalities=["AUDIO"],
#                 speech_config=speech_config,
#                 output_audio_transcription={},  # optional transcription
#             )
#         else:
#             run_config = RunConfig(response_modalities=["TEXT"])

#         live_request_queue = LiveRequestQueue()
#         live_events = runner.run_live(
#             session=session,
#             live_request_queue=live_request_queue,
#             run_config=run_config,
#         )

#         return live_events, live_request_queue
    
#     except Exception as e:
#         print(f"Error starting agent session: {e}")
#         raise

# # Add cleanup on shutdown
# @app.on_event("shutdown")
# async def shutdown_event():
#     """Clean up all active sessions on shutdown."""
#     for user_id, queue in list(active_sessions.items()):
#         try:
#             queue.close()
#         except Exception as e:
#             print(f"Error closing session {user_id}: {e}")
#     active_sessions.clear()
#     print("All sessions cleaned up.")

#============================================================================================================================================================================

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import base64
import warnings
import asyncio
import traceback

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

from fastapi import FastAPI, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from google.generativeai import GenerativeModel
import google.generativeai as genai

from host_agent import root_agent
# from tts_processor import generate_audio_from_text
# from stt_processor import process_audio_to_text
from audio.stt_processor import STTProcessor
from audio.tts_processor import TTSProcessor

tts_processor = TTSProcessor()

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

#
# ADK Streaming with Enhanced Multimodal Host Agent
#

# Load API Key
load_dotenv()

APP_NAME = "Pickleball Scheduling Agent"

audio_buffers = {}
session_queues = {}
stt_processors = {}


async def handle_stt_result(session_id: str, text: str):
    print(f"[STT DONE] {session_id}: {text}")
    # Send a message to the stream queue to start agent response
    queue = session_queues.get(session_id)
    if queue:
        await queue.put({"type": "query", "text": text})



genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
async def stream_gemini_tts(text: str):
    model = GenerativeModel("models/tts-1")
    stream = model.generate_audio(text, stream=True)

    for chunk in stream:
        if hasattr(chunk, "audio"):
            yield base64.b64encode(chunk.audio).decode("utf-8")


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
                # If it's text and (for partials or final responses), process accordingly.
                # if part.text:
                #     # When in audio mode, convert the text response using TTS.
                #     if is_audio:
                #         try:
                #             audio_data = generate_audio_from_text(part.text)
                #             if audio_data:
                #                 message = {
                #                     "mime_type": "audio/pcm",
                #                     "data": base64.b64encode(audio_data).decode("ascii")
                #                 }
                #                 yield f"data: {json.dumps(message)}\n\n"
                #                 print(f"[TTS Generated Audio]: {len(audio_data)} bytes.")
                #                 continue  # Skip sending text since we have audio
                #         except NotImplementedError as e:
                #             print(f"TTS not implemented: {e}")
                #             # If TTS is not available, fall back to text.
                    
                #     # Fallback: Send text as usual
                #     message = {
                #         "mime_type": "text/plain",
                #         "data": part.text
                #     }
                #     yield f"data: {json.dumps(message)}\n\n"
                #     print(f"[AGENT TO CLIENT]: text/plain: {message}")

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

STATIC_DIR = Path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Store active sessions
active_sessions = {}


@app.get("/")
async def root():
    """Serves the enhanced index.html for pickleball scheduling"""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "pickleball_host"}


@app.post("/start/{session_id}")
async def start_session(session_id: str):
    session_queues[session_id] = asyncio.Queue()
    print(f"✅ Session started: {session_id}")
    return {"status": "started"}


# @app.get("/events/{user_id}")
# async def sse_endpoint(user_id: int, is_audio: str = "false"):
#     """Enhanced SSE endpoint for multimodal agent to client communication"""

#     user_id_str = str(user_id)
    
#     try:
#         # Start agent session
#         live_events, live_request_queue = await start_agent_session(user_id_str, is_audio == "true")

#         # Store the request queue for this user
#         active_sessions[user_id_str] = live_request_queue

#         print(f"Pickleball Scheduling Client #{user_id} connected via SSE, audio mode: {is_audio}")

#         def cleanup():
#             try:
#                 live_request_queue.close()
#                 if user_id_str in active_sessions:
#                     del active_sessions[user_id_str]
#                 print(f"Pickleball Scheduling Client #{user_id} disconnected from SSE")
#             except Exception as e:
#                 print(f"Error during cleanup: {e}")

#         async def event_generator():
#             try:
#                 async for data in agent_to_client_sse(live_events):
#                     yield data
#             except Exception as e:
#                 print(f"Error in SSE stream: {e}")
#                 traceback.print_exc()
#                 # Send error to client before closing
#                 error_message = {
#                     "error": "Connection lost",
#                     "message": "Please refresh the page to reconnect"
#                 }
#                 yield f"data: {json.dumps(error_message)}\n\n"
#             finally:
#                 cleanup()

#         return StreamingResponse(
#             event_generator(),
#             media_type="text/event-stream",
#             headers={
#                 "Cache-Control": "no-cache",
#                 "Connection": "keep-alive",
#                 "Access-Control-Allow-Origin": "*",
#                 "Access-Control-Allow-Headers": "Cache-Control"
#             }
#         )
        
#     except Exception as e:
#         print(f"Error starting SSE session: {e}")
#         traceback.print_exc()
#         return {"error": f"Failed to start session: {str(e)}"}


# @app.get("/events/{session_id}")
# async def events(session_id: str):
#     async def event_generator():
#         queue = asyncio.Queue()
#         session_queues[session_id] = queue

#         try:
#             while True:
#                 item = await queue.get()

#                 if item["type"] == "query":
#                     # Call host agent stream
#                     async for chunk in root_agent.stream(item["text"], session_id=session_id):
#                         if chunk.get("is_task_complete"):
#                             full_text = chunk.get("content", "")

#                             # Send text response
#                             yield f"data: {json.dumps({'mime_type': 'text/plain', 'data': full_text})}\n\n"

#                             # Now stream TTS audio
#                             async for audio_chunk in tts_processor.stream_tts(full_text):
#                                 yield f"data: {json.dumps(audio_chunk)}\n\n"

#                             # Final signal
#                             yield f"data: {json.dumps({'turn_complete': True})}\n\n"

#         except asyncio.CancelledError:
#             print(f"🔌 SSE disconnected: {session_id}")
#         finally:
#             session_queues.pop(session_id, None)
#             stt_processors.pop(session_id, None)

#     return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/events/{session_id}")
async def stream_response(session_id: str, is_audio: str = Query("false")):
    """Streams response from the Host Agent + Gemini TTS."""

    is_audio = is_audio.lower() == "true"
    print(f"🎧 SSE Session Started: {session_id}, is_audio={is_audio}")

    if session_id not in session_queues:
        session_queues[session_id] = asyncio.Queue()

    async def event_generator():
        q = session_queues[session_id]
        if not q:
            yield "data: {}\n\n"
            return

        # Wait for input message (text)
        while True:
            if not q.empty():
                query = q.get()
                break
            await asyncio.sleep(0.1)

        # Call the Host Agent and stream its response
        # async for chunk in root_agent.stream(query=query, session_id=session_id):
        async for chunk in root_agent.stream(query=query, session_id=session_id):
            if chunk.get("is_task_complete"):
                text = chunk["content"]
                if text:
                    if is_audio:
                        # async for pcm_chunk in stream_gemini_tts(text):
                        async for pcm_chunk in tts_processor.stream_tts(text):
                            yield f"data: {json.dumps({'mime_type': 'audio/pcm', 'data': pcm_chunk})}\n\n"
                        yield f"data: {json.dumps({'turn_complete': True})}\n\n"
                    else:
                        # Send plain text message if TTS is disabled
                        for line in text.splitlines():
                            yield f"data: {json.dumps({'mime_type': 'text/plain', 'data': line})}\n\n"
                        yield f"data: {json.dumps({'turn_complete': True})}\n\n"
                break
            else:
                yield f"data: {json.dumps({'mime_type': 'text/plain', 'data': '.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# @app.post("/send/{user_id}")
# async def send_message_endpoint(user_id: int, request: Request):
#     """Enhanced HTTP endpoint for client to multimodal agent communication"""

#     user_id_str = str(user_id)

#     try:
#         # Get the live request queue for this user
#         live_request_queue = active_sessions.get(user_id_str)
#         if not live_request_queue:
#             return {"error": "Session not found"}

#         # Parse the message
#         message = await request.json()
#         mime_type = message["mime_type"]
#         data = message["data"]

#         # Send the message to the agent
#         if mime_type == "text/plain":
#             content = Content(role="user", parts=[Part.from_text(text=data)])
#             live_request_queue.send_content(content=content)
#             print(f"[CLIENT TO AGENT]: {data}")
#         elif mime_type == "audio/pcm":
#             decoded_data = base64.b64decode(data)
#             live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
#             print(f"[CLIENT TO AGENT]: audio/pcm: {len(decoded_data)} bytes")
#         else:
#             return {"error": f"Mime type not supported: {mime_type}"}

#         return {"status": "sent"}
        
#     except Exception as e:
#         print(f"Error sending message: {e}")
#         traceback.print_exc()
#         return {"error": f"Failed to send message: {str(e)}"}


# @app.post("/send/{user_id}")
# async def send_message_endpoint(user_id: int, request: Request):
#     """Enhanced HTTP endpoint for client to multimodal agent communication"""
#     user_id_str = str(user_id)

#     try:
#         # Get the live request queue for this user
#         live_request_queue = active_sessions.get(user_id_str)
#         if not live_request_queue:
#             return {"error": "Session not found"}

#         # Parse the incoming message
#         message = await request.json()
#         mime_type = message["mime_type"]
#         data = message["data"]

#         if mime_type == "text/plain":
#             content = Content(role="user", parts=[Part.from_text(text=data)])
#             live_request_queue.send_content(content=content)
#             print(f"[CLIENT TO AGENT]: {data}")
#         elif mime_type == "audio/pcm":
#             # Decode and buffer the audio data
#             decoded_data = base64.b64decode(data)
#             if user_id_str not in audio_buffers:
#                 audio_buffers[user_id_str] = bytearray()
#             audio_buffers[user_id_str].extend(decoded_data)
#             print(f"[CLIENT TO AGENT][STT Buffer]: Received and buffered {len(decoded_data)} bytes.")
#             # Note: We return buffering status and do NOT yet send to the agent.
#             return {"status": "buffering"}
#         else:
#             return {"error": f"Mime type not supported: {mime_type}"}

#         return {"status": "sent"}
        
#     except Exception as e:
#         print(f"Error sending message: {e}")
#         traceback.print_exc()
#         return {"error": f"Failed to send message: {str(e)}"}


@app.post("/send/{session_id}")
async def send(session_id: str, req: Request):
    payload = await req.json()
    mime_type = payload.get("mime_type")
    data = payload.get("data")

    if session_id not in session_queues:
        return {"error": "Invalid session_id"}

    if mime_type == "text/plain":
        print(f"[TEXT] {data}")
        await session_queues[session_id].put({"type": "query", "text": data})

    elif mime_type == "audio/pcm":
        # Decode Base64 audio data
        try:
            pcm_bytes = base64.b64decode(data)
            if session_id not in stt_processors:
                stt = STTProcessor()
                stt.start(lambda text: asyncio.create_task(handle_stt_result(session_id, text)))
                stt_processors[session_id] = stt

            stt_processors[session_id].add_pcm_chunk(pcm_bytes)
        except Exception as e:
            print(f"❌ Error processing audio: {e}")
            return {"error": str(e)}

    return {"status": "received"}


# @app.post("/end_audio/{user_id}")
# async def end_audio_endpoint(user_id: int):
#     """Endpoint to trigger STT processing on buffered audio and send the transcript to the Host Agent."""
#     user_id_str = str(user_id)
#     if user_id_str not in audio_buffers or len(audio_buffers[user_id_str]) == 0:
#         return {"error": "No audio to process."}
    
#     # Import the STT processor
    
#     # Get and clear the buffered audio
#     pcm_data = bytes(audio_buffers[user_id_str])
#     audio_buffers[user_id_str] = bytearray()
    
#     transcript = process_audio_to_text(pcm_data)
#     print(f"[STT Transcript]: {transcript}")
    
#     # Now send the transcript as a text message to the host agent session
#     live_request_queue = active_sessions.get(user_id_str)
#     if not live_request_queue:
#         return {"error": "Session not found."}
    
#     content = Content(role="user", parts=[Part.from_text(text=transcript)])
#     live_request_queue.send_content(content=content)
    
#     return {"status": "sent", "transcript": transcript}


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

@app.post("/stop_stt/{session_id}")
async def stop_stt(session_id: str):
    if session_id in stt_processors:
        stt_processors[session_id].terminate()
        del stt_processors[session_id]
        print(f"🛑 STTProcessor terminated for {session_id}")
    return {"status": "stopped"}


# Development server startup
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="localhost", # 0.0.0.0
        port=7000, 
        reload=True,
        log_level="info"
    )