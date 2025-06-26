# import streamlit as st
# import threading
# import requests
# import queue
# from sseclient import SSEClient
# from recorder import PCMRecorder
# from player import PCMPlayer
# import json
# import base64

# # --- Configuration ---
# session_id = "2339941" # Replace with your actual session ID or generate dynamically
# API = "http://127.0.0.1:7000" # Adjust this to your API URL based on your setup
# SEND_URL = f"{API}/send/{session_id}"
# EVENTS_URL = f"{API}/events/{session_id}?is_audio=true"

# # --- Initialize Session State & Queue ---
# if "messages" not in st.session_state:
#     st.session_state.messages = []
# if "sse_started" not in st.session_state:
#     st.session_state.sse_started = False
# # new added
# if "player" not in st.session_state:
#     st.session_state.player = PCMPlayer()

# msg_queue = queue.Queue()

# # --- SSE Listener Thread ---
# def sse_listener():
#     client = SSEClient(
#         EVENTS_URL,
#         session=requests.Session(),
#         headers={"Accept": "text/event-stream"}
#     )
#     for ev in client:
#         try:
#             parsed = json.loads(ev.data)
#             mime_type = parsed.get("mime_type")
#             if mime_type == "text/plain":
#                 msg_queue.put("🗣️ " + parsed["data"])
#             elif mime_type == "audio/pcm":
#                 audio_data = base64.b64decode(parsed["data"])
#                 st.session_state.player.write(audio_data) # new added
#                 st.session_state.player.stream.stop_stream()
#                 st.session_state.player.stream.start_stream() # Restart stream to play immediately
#             else:
#                 msg_queue.put("🤖 Unknown mime_type")
#         except Exception as e:
#             msg_queue.put(f"[SSE Error]: {e}")

# # Start SSE only once
# if not st.session_state.sse_started:
#     threading.Thread(target=sse_listener, daemon=True).start()
#     st.session_state.sse_started = True


# # --- UI ---
# st.title("ADK Streaming Test")

# # Drain the queue on every rerun (before rendering the UI)
# while not msg_queue.empty():
#     st.session_state.messages.append(msg_queue.get())

# msgs_placeholder = st.empty()
# # with msgs_placeholder.container():
# #     for m in st.session_state.messages:
# #         st.markdown(m)
# for message in st.session_state.messages:
#     with st.chat_message("user" if message.startswith("👤") else "assistant"):
#         st.markdown(message.replace("👤 ", "").replace("🗣️ ", ""))

# # Send callback
# def on_send():
#     msg = st.session_state.text_input.strip()
#     if msg:
#         requests.post(SEND_URL, json={"mime_type": "text/plain", "data": msg})
#         st.session_state.messages.append("👤 " + msg)
#         st.session_state.text_input = ""

# # Audio callback
# # def on_start_audio():
# #     st.session_state.messages.append("🎙️ Audio mode started")
# #     recorder = PCMRecorder()
# #     player = PCMPlayer()
# #     globals()["player"] = player

# #     def record_and_send():
# #         while True:
# #             try:
# #                 audio_chunk = recorder.read()
# #                 encoded = base64.b64encode(audio_chunk).decode("ascii")
# #                 requests.post(SEND_URL, json={
# #                     "mime_type": "audio/pcm",
# #                     "data": encoded
# #                 })
# #             except Exception as e:
# #                 print("Audio recording failed:", e)
# #                 break

# #     threading.Thread(target=record_and_send, daemon=True).start()
# def on_start_audio():
#     if "recorder" not in st.session_state:
#         st.session_state.recorder = PCMRecorder()
#         st.session_state.messages.append("🎙️ Audio mode started")
        
#         def record_and_send():
#             while hasattr(st.session_state, "recorder"):
#                 try:
#                     audio_chunk = st.session_state.recorder.read()
#                     encoded = base64.b64encode(audio_chunk).decode("ascii")
#                     requests.post(SEND_URL, json={
#                         "mime_type": "audio/pcm",
#                         "data": encoded
#                     })
#                 except Exception as e:
#                     print("Audio error:", e)
#                     break

#         threading.Thread(target=record_and_send, daemon=True).start()
#     # Save player to use in SSE handler (or pass to global if needed)
#     # globals()["player"] = player

# # Input field + buttons (callback-based)
# st.text_input("Type your message", key="text_input", label_visibility="collapsed")
# st.button("Send", on_click=on_send)
# st.button("Start Audio", on_click=on_start_audio, type="primary") # optional type="primary" for primary button style

import streamlit as st
import threading
import requests
import queue
from sseclient import SSEClient
from recorder import PCMRecorder
from player import PCMPlayer
import json
import base64
import time

# --- Configuration ---
session_id = "2339941"  # Use a fixed session ID for now
API = "http://127.0.0.1:7000"
SEND_URL = f"{API}/send/{session_id}"
EVENTS_URL = f"{API}/events/{session_id}?is_audio=true"

# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "recording" not in st.session_state:
    st.session_state.recording = False
    
if "player" not in st.session_state:
    st.session_state.player = PCMPlayer()
    
if "recorder" not in st.session_state:
    st.session_state.recorder = None

# Create a thread-safe queue for SSE messages
if "message_queue" not in st.session_state:
    st.session_state.message_queue = queue.Queue()

# --- SSE Listener Thread ---
def sse_listener():
    while True:
        try:
            client = SSEClient(
                EVENTS_URL,
                session=requests.Session(),
                headers={"Accept": "text/event-stream"}
            )
            for ev in client:
                try:
                    parsed = json.loads(ev.data)
                    # Put message in queue
                    st.session_state.message_queue.put(parsed)
                except Exception as e:
                    print(f"SSE parsing error: {e}")
        except Exception as e:
            print(f"SSE connection error: {e}")
            time.sleep(2)  # Reconnect after 2 seconds

# Start SSE listener in a daemon thread
if "sse_thread" not in st.session_state:
    st.session_state.sse_thread = threading.Thread(target=sse_listener, daemon=True)
    st.session_state.sse_thread.start()
    print("SSE listener started")

# --- UI ---
st.title("Pickleball Scheduling Assistant")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Process incoming messages from the queue
if not st.session_state.message_queue.empty():
    # Create a copy of messages to process
    messages_to_process = []
    while not st.session_state.message_queue.empty():
        messages_to_process.append(st.session_state.message_queue.get_nowait())
    
    # Process each message
    for msg in messages_to_process:
        mime_type = msg.get("mime_type")
        
        if mime_type == "text/plain":
            text = msg["data"]
            st.session_state.messages.append({"role": "assistant", "content": text})
            print(f"Added text message: {text}")
            
        elif mime_type == "audio/pcm":
            try:
                audio_data = base64.b64decode(msg["data"])
                st.session_state.player.write(audio_data)
                print("Played audio chunk")
            except Exception as e:
                print(f"Audio playback error: {e}")
    
    # Rerun to update the UI with new messages
    st.experimental_rerun()

# User input
if prompt := st.chat_input("Type your message"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Send to agent
    requests.post(SEND_URL, json={"mime_type": "text/plain", "data": prompt})
    print(f"Sent message: {prompt}")

# Audio controls
col1, col2 = st.columns(2)

with col1:
    if st.button("🎤 Start Recording", disabled=st.session_state.recording):
        st.session_state.recording = True
        st.session_state.recorder = PCMRecorder()
        
        def record_and_send():
            while st.session_state.recording:
                try:
                    audio_chunk = st.session_state.recorder.read()
                    encoded = base64.b64encode(audio_chunk).decode("ascii")
                    requests.post(SEND_URL, json={
                        "mime_type": "audio/pcm",
                        "data": encoded
                    })
                    print("Sent audio chunk")
                except Exception as e:
                    print(f"Recording error: {e}")
                    break
                    
        threading.Thread(target=record_and_send, daemon=True).start()
        st.session_state.messages.append({"role": "system", "content": "Recording started..."})
        st.experimental_rerun()

with col2:
    if st.button("⏹️ Stop Recording", disabled=not st.session_state.recording):
        st.session_state.recording = False
        if st.session_state.recorder:
            st.session_state.recorder.close()
            st.session_state.recorder = None
        st.session_state.messages.append({"role": "system", "content": "Recording stopped"})
        st.experimental_rerun()

# Status indicator
if st.session_state.recording:
    st.warning("Recording in progress... Speak now")

# Add debug information
st.sidebar.subheader("Debug Info")
st.sidebar.write(f"Messages in queue: {st.session_state.message_queue.qsize()}")
st.sidebar.write(f"Total messages: {len(st.session_state.messages)}")
if st.sidebar.button("Force Rerun"):
    st.experimental_rerun()