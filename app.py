import numpy as np
import pvporcupine
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import time
import base64
import websockets
import asyncio

app = FastAPI()

porcupine = pvporcupine.create(
    access_key="8+8UgimaYCMHvycSUUkHUgNdmGFxKrIABzuCWwpDd2fVt69ewUEDCw==",
    keyword_paths=["Hey-Jamie_en_linux_v3_0_0.ppn"],
    sensitivities=[0.5]
)

# Store active WebSocket connections for each call
active_calls = {}

async def process_audio_stream(call_id: str, websocket_url: str):
    """Connect to Vapi's WebSocket to receive audio and process it with Porcupine."""
    try:
        async with websockets.connect(websocket_url) as websocket:
            print(f"Connected to WebSocket for call {call_id}: {websocket_url}")
            while True:
                # Receive audio data from Vapi's WebSocket
                data = await websocket.recv()
                audio_frame = np.frombuffer(data, dtype=np.int16)
                if len(audio_frame) == porcupine.frame_length:
                    keyword_index = porcupine.process(audio_frame)
                    if keyword_index >= 0:
                        print(f"Detected 'Hey Jamie' for call {call_id}!")
                        # Notify Vapi via an HTTP POST (you may need a separate endpoint or mechanism)
                        return {"status": "wake_word_detected"}
                else:
                    print(f"Audio frame length mismatch for call {call_id}: {len(audio_frame)}")
    except Exception as e:
        print(f"WebSocket error for call {call_id}: {e}")
        return {"status": "no_wake_word"}
    finally:
        if call_id in active_calls:
            del active_calls[call_id]

@app.get("/")
async def root():
    return {"message": "Hey Jamie Server is running"}

@app.post("/events")
async def handle_vapi_events(request: Request):
    try:
        event = await request.json()
        print(f"Received event payload: {event}")

        message = event.get("message", {})
        message_type = message.get("type")
        call_id = event.get("call", {}).get("id")

        if not call_id:
            return JSONResponse(content={"status": "error", "message": "No call ID found"})

        if message_type == "speech-update" and message.get("status") == "started" and message.get("role") == "user":
            # Check if this call already has an active WebSocket connection
            if call_id not in active_calls:
                # Extract WebSocket URL from the event
                websocket_url = event.get("call", {}).get("monitor", {}).get("listenUrl")
                if not websocket_url:
                    print(f"No WebSocket URL found for call {call_id}")
                    return JSONResponse(content={"status": "no_wake_word"})

                # Start processing audio stream in the background
                active_calls[call_id] = asyncio.create_task(process_audio_stream(call_id, websocket_url))
            
            # Wait for the task to complete (or timeout)
            try:
                result = await asyncio.wait_for(active_calls[call_id], timeout=5.0)
                return JSONResponse(content=result)
            except asyncio.TimeoutError:
                print(f"Timeout waiting for wake word detection for call {call_id}")
                return JSONResponse(content={"status": "no_wake_word"})

        return JSONResponse(content={"status": "no_wake_word"})
    except Exception as e:
        print(f"Error processing event: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.on_event("shutdown")
def cleanup():
    porcupine.delete()
