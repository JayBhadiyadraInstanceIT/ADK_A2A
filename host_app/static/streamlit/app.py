# # app.py
# import streamlit as st
# import threading, requests, base64
# from recorder import PCMRecorder
# from player import PCMPlayer

# st.title("📡 Pure-Python Host-Agent UI")

# session_id = st.experimental_session_state.get("session_id") or None
# if not session_id:
#     session_id = base64.urlsafe_b64encode(st.session_state.get("session_id_bytes", b"") or b"").decode() or None
#     st.experimental_session_state.session_id = session_id

# rec = st.session_state.get("recorder")
# ply = st.session_state.get("player")
# running = st.session_state.get("running", False)
# buffer = []

# API_URL = "http://localhost:8000"
# send_url = f"{API_URL}/send/{session_id}"
# events_url = f"{API_URL}/events/{session_id}"

# def listen_sse():
#     import sseclient
#     resp = requests.get(events_url, stream=True)
#     client = sseclient.SSEClient(resp)
#     for ev in client:
#         msg = ev.data  # JSON
#         st.session_state.last_msg = msg
#         st.experimental_rerun()

# if st.button("Connect SSE"):
#     st.session_state.running = True
#     threading.Thread(target=listen_sse, daemon=True).start()

# col1, col2 = st.columns(2)
# if col1.button("Start Audio"):
#     rec = PCMRecorder()
#     ply = PCMPlayer()
#     st.session_state.recorder = rec
#     st.session_state.player = ply
#     st.session_state.running = True
#     def rec_loop():
#         buffer = []
#         while st.session_state.running:
#             data = rec.read()
#             buffer.append(data)
#             ply.write(data)
#             if len(buffer) >= int(16000*0.2/rec.chunk):
#                 payload = base64.b64encode(b"".join(buffer)).decode()
#                 requests.post(send_url, json={"mime_type":"audio/pcm","data":payload})
#                 buffer.clear()
#     threading.Thread(target=rec_loop, daemon=True).start()

# if col2.button("Stop Audio"):
#     st.session_state.running = False
#     rec.close()
#     ply.close()

# text = st.text_input("Send Text:")
# if st.button("Send"):
#     requests.post(send_url, json={"mime_type":"text/plain","data": text})

# st.write("Last message from server:", st.session_state.get("last_msg"))

# ========================================================================================================================================================================

import streamlit as st
import threading
import requests
import queue
from sseclient import SSEClient
from recorder import PCMRecorder
from player import PCMPlayer

# --- Configuration ---
session_id = "default"
API = "http://127.0.0.1:8000"
SEND_URL = f"{API}/send/{session_id}"
EVENTS_URL = f"{API}/events/{session_id}"

# --- Initialize Session State & Queue ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sse_started" not in st.session_state:
    st.session_state.sse_started = False

msg_queue = queue.Queue()

# --- SSE Listener Thread ---
def sse_listener():
    client = SSEClient(
        EVENTS_URL,
        session=requests.Session(),
        headers={"Accept": "text/event-stream"}
    )
    for ev in client:
        msg_queue.put("🤖 " + ev.data)

if not st.session_state.sse_started:
    threading.Thread(target=sse_listener, daemon=True).start()
    st.session_state.sse_started = True

# --- Consume queued messages ---
while not msg_queue.empty():
    st.session_state.messages.append(msg_queue.get())
    st.experimental_rerun()

# --- UI ---
st.title("ADK Streaming Test")

# Message display
for m in st.session_state.messages:
    st.write(m)

# Send callback
def on_send():
    msg = st.session_state.text_input.strip()
    if msg:
        requests.post(SEND_URL, json={"mime_type": "text/plain", "data": msg})
        st.session_state.messages.append("👤 " + msg)
        st.session_state.text_input = ""

# Audio callback
def on_start_audio():
    st.session_state.messages.append("🎙️ Audio mode started")
    # TODO: integrate PCMRecorder + PCMPlayer logic here

# Input field + buttons (callback-based)
st.text_input("Type your message", key="text_input", label_visibility="collapsed")
st.button("Send", on_click=on_send)
st.button("Start Audio", on_click=on_start_audio)
