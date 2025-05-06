import numpy as np
import pvporcupine
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import time
from pydantic import BaseModel
import base64

app = FastAPI()

porcupine = pvporcupine.create(
    access_key="8+8UgimaYCMHvycSUUkHUgNdmGFxKrIABzuCWwpDd2fVt69ewUEDCw==",  # Ensure this matches your new Access Key
    keyword_paths=["Hey-Jamie_en_linux_v3_0_0.ppn"],
    sensitivities=[0.5]
)

@app.get("/")
async def root():
    return {"message": "Hey Jamie Server is running"}

# Model for Vapi event payload (adjust based on actual payload structure)
class VapiEvent(BaseModel):
    type: str
    audio: str | None = None  # Base64-encoded audio (if Vapi sends audio this way)

# HTTP endpoint for Vapi to send events
@app.post("/events")
async def handle_vapi_events(event: VapiEvent, request: Request):
    try:
        print(f"Received event: {event.type}")
        if event.audio:
            # Decode base64 audio data (adjust based on Vapi's event structure)
            audio_data = base64.b64decode(event.audio)
            audio_frame = np.frombuffer(audio_data, dtype=np.int16)
            keyword_index = porcupine.process(audio_frame)
            if keyword_index >= 0:
                print("Detected 'Hey Jamie'!")
                return JSONResponse(content={"message": "Hey Jamie detected"})
        return JSONResponse(content={"message": "No wake word detected"})
    except Exception as e:
        print(f"Error processing event: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Cleanup on shutdown
@app.on_event("shutdown")
def cleanup():
    porcupine.delete()
