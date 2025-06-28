/**
 * app.js: JS code for the adk-streaming sample app.
 */

/**
 * SSE (Server-Sent Events) handling
 */

// Connect the server with SSE
const sessionId = Math.random().toString().substring(10);
const sse_url =
  "http://" + window.location.host + "/events/" + sessionId;
const send_url =
  "http://" + window.location.host + "/send/" + sessionId;
let eventSource = null;
let is_audio = false;

// Get DOM elements
const messageForm = document.getElementById("messageForm");
const messageInput = document.getElementById("message");
const messagesDiv = document.getElementById("messages");
let currentMessageId = null;

// SSE handlers
function connectSSE() {
  // Connect to SSE endpoint
  eventSource = new EventSource(sse_url + "?is_audio=" + is_audio);

  // Handle connection open
  eventSource.onopen = function () {
    // Connection opened messages
    console.log("SSE connection opened.");
    document.getElementById("messages").textContent = "Connection opened";

    // Enable the Send button
    document.getElementById("sendButton").disabled = false;
    addSubmitHandler();
  };

  // Handle incoming messages
  eventSource.onmessage = function (event) {
    // Parse the incoming message
    const message_from_server = JSON.parse(event.data);
    console.log("[AGENT TO CLIENT] ", message_from_server);

    // Check if the turn is complete
    // if turn complete, add new message
    if (
      message_from_server.turn_complete &&
      message_from_server.turn_complete == true
    ) {
      currentMessageId = null;
      return;
    }

    // Check for interrupt message
    if (
      message_from_server.interrupted &&
      message_from_server.interrupted === true
    ) {
      // Stop audio playback if it's playing
      if (audioPlayerNode) {
        audioPlayerNode.port.postMessage({ command: "endOfAudio" });
      }
      return;
    }

    // If it's audio, play it
    if (message_from_server.mime_type == "audio/pcm" && audioPlayerNode) {
      audioPlayerNode.port.postMessage(base64ToArray(message_from_server.data));
    }

    // If it's a text, print it
    if (message_from_server.mime_type == "text/plain") {
      // add a new message for a new turn
      if (currentMessageId == null) {
        currentMessageId = Math.random().toString(36).substring(7);
        const message = document.createElement("p");
        message.id = currentMessageId;
        // Append the message element to the messagesDiv
        messagesDiv.appendChild(message);
      }

      // Add message text to the existing message element
      const message = document.getElementById(currentMessageId);
      message.textContent += message_from_server.data;

      // Scroll down to the bottom of the messagesDiv
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
      // Stream each sentence as TTS
      if (audioEnabled) {
        fetch("/tts-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: message_from_server.data })
        })
        .then(res => res.json())
        .then(audio => {
          if (audio.data) {
            const audioBytes = base64ToArray(audio.data);
            if (audioPlayerNode) {
              audioPlayerNode.port.postMessage(audioBytes);
            }
          }
        })
        .catch(err => console.error("TTS stream error:", err));
      }
    }
  };

  // Handle connection close
  eventSource.onerror = function (event) {
    console.log("SSE connection error or closed.");
    document.getElementById("sendButton").disabled = true;
    document.getElementById("messages").textContent = "Connection closed";
    eventSource.close();
    setTimeout(function () {
      console.log("Reconnecting...");
      connectSSE();
    }, 5000);
  };
}
connectSSE();

// Add submit handler to the form
function addSubmitHandler() {
  messageForm.onsubmit = function (e) {
    e.preventDefault();
    const message = messageInput.value;
    if (message) {
      const p = document.createElement("p");
      p.textContent = "> " + message;
      messagesDiv.appendChild(p);
      messageInput.value = "";
      sendMessage({
        mime_type: "text/plain",
        data: message,
      });
      console.log("[CLIENT TO AGENT] " + message);
    }
    return false;
  };
}

// Send a message to the server via HTTP POST
async function sendMessage(message) {
  try {
    const response = await fetch(send_url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(message)
    });
    
    if (!response.ok) {
      console.error('Failed to send message:', response.statusText);
    }
  } catch (error) {
    console.error('Error sending message:', error);
  }
}

// Decode Base64 data to Array
function base64ToArray(base64) {
  const binaryString = window.atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Audio handling
 */

let audioPlayerNode;
let audioPlayerContext;
let audioRecorderNode;
let audioRecorderContext;
let micStream;

// Audio buffering for 0.2s intervals
let audioBuffer = [];
let bufferTimer = null;

// Import the audio worklets
import { startAudioPlayerWorklet } from "./audio-player.js";
import { startAudioRecorderWorklet } from "./audio-recorder.js";

// Start audio
function startAudio() {
  // Start audio output
  startAudioPlayerWorklet().then(([node, ctx]) => {
    audioPlayerNode = node;
    audioPlayerContext = ctx;
  });
  // Start audio input
  startAudioRecorderWorklet(audioRecorderHandler).then(
    ([node, ctx, stream]) => {
      audioRecorderNode = node;
      audioRecorderContext = ctx;
      micStream = stream;
    }
  );
}

// Start the audio only when the user clicked the button
// (due to the gesture requirement for the Web Audio API)
const startAudioButton = document.getElementById("startAudioButton");
startAudioButton.addEventListener("click", () => {
  startAudioButton.disabled = true;
  startAudio();
  is_audio = true;
  eventSource.close(); // close current connection
  connectSSE(); // reconnect with the audio mode
});

// Audio recorder handler
function audioRecorderHandler(pcmData) {
  // Add audio data to buffer
  audioBuffer.push(new Uint8Array(pcmData));
  
  // Start timer if not already running
  if (!bufferTimer) {
    bufferTimer = setInterval(sendBufferedAudio, 5000); // 0.2 seconds
  }
}

// Send buffered audio data every 0.2 seconds
function sendBufferedAudio() {
  if (audioBuffer.length === 0) {
    return;
  }
  
  // Merge all Float32 PCM chunks
  let float32 = new Float32Array(audioBuffer.reduce((sum, buf) => sum + buf.length, 0));
  let offset = 0;
  for (let chunk of audioBuffer) {
    float32.set(new Float32Array(chunk.buffer), offset);
    offset += chunk.length;
  }

  // Convert Float32 to Int16 PCM (what WAV expects)
  let int16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    let s = Math.max(-1, Math.min(1, float32[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }

  // Create proper WAV blob from Int16
  const wavBlob = createWavBlob(int16.buffer);
  console.log("WAV Blob Preview", wavBlob.slice(0, 12).arrayBuffer().then(b => new Uint8Array(b)));
  sendToSTT(wavBlob);

  audioBuffer = [];
}
  // Calculate total length
//   let totalLength = 0;
//   for (const chunk of audioBuffer) {
//     totalLength += chunk.length;
//   }
  
//   // Combine all chunks into a single buffer
//   const combinedBuffer = new Uint8Array(totalLength);
//   let offset = 0;
//   for (const chunk of audioBuffer) {
//     combinedBuffer.set(chunk, offset);
//     offset += chunk.length;
//   }
  
//   // Send the combined audio data
//   // sendMessage({
//   //   mime_type: "audio/pcm",
//   //   data: arrayBufferToBase64(combinedBuffer.buffer),
//   // });
//   const wavBlob = createWavBlob(combinedBuffer.buffer);
//   sendToSTT(wavBlob);

//   // sendToSTT(new Blob([combinedBuffer], { type: "audio/wav" }));
//   // console.log("[CLIENT TO AGENT] sent %s bytes", combinedBuffer.byteLength);
  
//   // Clear the buffer
//   audioBuffer = [];
// }

// Stop audio recording and cleanup
function stopAudioRecording() {
  if (bufferTimer) {
    clearInterval(bufferTimer);
    bufferTimer = null;
  }
  
  // Send any remaining buffered audio
  if (audioBuffer.length > 0) {
    sendBufferedAudio();
  }
}

// Encode an array buffer with Base64
function arrayBufferToBase64(buffer) {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}


async function sendToSTT(blob) {
  const formData = new FormData();
  formData.append("file", blob, "audio.wav");
  formData.append("service", "openai");

  try {
    const response = await fetch("/stt-stream", {
      method: "POST",
      body: formData,
    });

    const result = await response.json();
    const text = result.text;
    if (text) {
      console.log("[STT -> TEXT] ", text);
      sendMessage({
        mime_type: "text/plain",
        data: text});
      } else {
      console.warn("[STT] No transcription returned.");
      }
    }
   catch (error) {
    console.error("STT request failed:", error);
  }
}

function createWavBlob(pcmBuffer, sampleRate = 16000) {
  const float32Array = new Float32Array(pcmBuffer);
  const int16Array = new Int16Array(float32Array.length);

  // Convert Float32 [-1.0, 1.0] to Int16 [-32768, 32767]
  for (let i = 0; i < float32Array.length; i++) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }

  const byteLength = int16Array.length * 2;
  const wavHeader = new ArrayBuffer(44);
  const view = new DataView(wavHeader);

  let offset = 0;
  const writeString = (str) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset++, str.charCodeAt(i));
    }
  };

  writeString('RIFF');
  view.setUint32(offset, 36 + byteLength, true); offset += 4;
  writeString('WAVE');
  writeString('fmt ');
  view.setUint32(offset, 16, true); offset += 4;
  view.setUint16(offset, 1, true); offset += 2; // PCM format
  view.setUint16(offset, 1, true); offset += 2; // Mono
  view.setUint32(offset, sampleRate, true); offset += 4;
  view.setUint32(offset, sampleRate * 2, true); offset += 4; // Byte rate
  view.setUint16(offset, 2, true); offset += 2; // Block align
  view.setUint16(offset, 16, true); offset += 2; // Bits per sample
  writeString('data');
  view.setUint32(offset, byteLength, true); offset += 4;

  const wavBytes = new Uint8Array(44 + byteLength);
  wavBytes.set(new Uint8Array(wavHeader), 0);
  wavBytes.set(new Uint8Array(int16Array.buffer), 44);

  return new Blob([wavBytes], { type: 'audio/wav' });
}

