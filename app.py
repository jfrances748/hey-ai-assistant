import numpy as np
import pvporcupine
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import time
import base64
import websockets
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        # Add headers if Vapi requires authentication (replace with your API key)
        headers = {
            "Authorization": "2adc4682-66f6-47d4-9c9f-aad24a73650b"  #
        }
        logger.info(f"Attempting to connect to WebSocket for call {call_id}: {websocket_url}")
        async with websockets.connect(websocket_url, extra_headers=headers) as websocket:
            logger.info(f"Successfully connected to WebSocket for call {call_id}")
            while True:
                # Receive audio data from Vapi's WebSocket
                data = await websocket.recv()
                logger.debug(f"Received audio data for call {call_id}: {len(data)} bytes")
                audio_frame = np.frombuffer(data, dtype=np.int16)
                if len(audio_frame) == porcupine.frame_length:
                    keyword_index = porcupine.process(audio_frame)
                    if keyword_index >= 0:
                        logger.info(f"Detected 'Hey Jamie' for call {call_id}!")
                        return {"status": "wake_word_detected"}
                else:
                    logger.warning(f"Audio frame length mismatch for call {call_id}: {len(audio_frame)} expected {porcupine.frame_length}")
    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"WebSocket connection failed for call {call_id}: Invalid status code {e.status_code}")
        return {"status": "no_wake_word"}
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"WebSocket connection closed for call {call_id}: {e}")
        return {"status": "no_wake_word"}
    except Exception as e:
        logger.error(f"WebSocket error for call {call_id}: {str(e)}")
        return {"status": "no_wake_word"}
    finally:
        if call_id in active_calls:
            del active_calls[call_id]
            logger.info(f"Cleaned up WebSocket task for call {call_id}")

@app.get("/")
async def root():
    return {"message": "Hey Jamie Server is running"}

@app.post("/events")
async def handle_vapi_events(request: Request):
    try:
        event = await request.json()
        logger.info(f"Received event payload: {event}")

        # Extract call_id with more robust checks and logging
        call_id = None
        if "call" in event and isinstance(event["call"], dict):
            call_id = event["call"].get("id")
        else:
            logger.error(f"Event structure missing 'call' key or not a dict: {event}")
            return JSONResponse(content={"status": "error", "message": "No call ID found"})

        if not call_id:
            logger.error(f"No call ID found in event: {event}")
            return JSONResponse(content={"status": "error", "message": "No call ID found"})

        logger.info(f"Processing event for call ID: {call_id}")

        message = event.get("message", {})
        message_type = message.get("type")

        if message_type == "speech-update" and message.get("status") == "started" and message.get("role") == "user":
            # Check if this call already has an active WebSocket connection
            if call_id not in active_calls:
                # Extract WebSocket URL from the event
                websocket_url = event.get("call", {}).get("monitor", {}).get("listenUrl")
                if not websocket_url:
                    logger.error(f"No WebSocket URL found for call {call_id}")
                    return JSONResponse(content={"status": "no_wake_word"})

                # Start processing audio stream in the background
                logger.info(f"Starting WebSocket task for call {call_id}")
                active_calls[call_id] = asyncio.create_task(process_audio_stream(call_id, websocket_url))
            
            # Wait for the task to complete (or timeout)
            try:
                result = await asyncio.wait_for(active_calls[call_id], timeout=5.0)
                logger.info(f"WebSocket task result for call {call_id}: {result}")
                return JSONResponse(content=result)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for wake word detection for call {call_id}")
                return JSONResponse(content={"status": "no_wake_word"})

        return JSONResponse(content={"status": "no_wake_word"})
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.on_event("shutdown")
def cleanup():
    porcupine.delete()
    logger.info("Porcupine resources cleaned up")
