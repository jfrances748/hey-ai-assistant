import numpy as np
import pvporcupine
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import time
import base64

app = FastAPI()

porcupine = pvporcupine.create(
    access_key="8+8UgimaYCMHvycSUUkHUgNdmGFxKrIABzuCWwpDd2fVt69ewUEDCw==",  # 
    keyword_paths=["Hey-Jamie_en_linux_v3_0_0.ppn"],
    sensitivities=[0.5]
)

@app.get("/")
async def root():
    return {"message": "Hey Jamie Server is running"}

# HTTP endpoint for Vapi to send events
@app.post("/events")
async def handle_vapi_events(request: Request):
    try:
        # Get the raw JSON payload
        event = await request.json()
        print(f"Received event payload: {event}")

        # Check if the event contains audio data (adjust based on actual payload structure)
        audio_data = None
        # Example: If audio is in a field like event["audio"]
        if "audio" in event:
            audio_data = base64.b64decode(event["audio"])
        # Example: If audio is in a nested field or URL, adjust accordingly
        # elif "data" in event and "audio" in event["data"]:
        #     audio_data = base64.b64decode(event["data"]["audio"])
        # elif "url" in event:
        #     async with httpx.AsyncClient() as client:
        #         response = await client.get(event["url"])
        #         audio_data = response.content

        if audio_data:
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
