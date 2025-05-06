import numpy as np
import pvporcupine
from fastapi import FastAPI, WebSocket
import os
import time

app = FastAPI()

# Initialize Porcupine
access_key = "8+8UgimaYCMHvycSUUkHUgNdmGFxKrIABzuCWwpDd2fVt69ewUEDCw=="
porcupine = pvporcupine.create(
    access_key=access_key,
    keyword_paths=["Hey-Jamie_en_linux_v3_0_0.ppn"],
    sensitivities=[0.5]
)

@app.get("/")
async def root():
    return {"message": "Hey AI Server is running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected")
    try:
        while True:
            # Receive audio data (16-bit PCM, 16 kHz)
            data = await websocket.receive_bytes()
            pcm = np.frombuffer(data, dtype=np.int16)
            if len(pcm) == porcupine.frame_length:
                result = porcupine.process(pcm)
                if result >= 0:
                    detection_time = time.ctime()
                    print(f"Detected 'Hey AI' at {detection_time}")
                    await websocket.send_text("Hey Jaime detected")
                    with open("detections.log", "a") as log:
                        log.write(f"Detected 'Hey AI' at {detection_time}\n")
            else:
                await websocket.send_text("Invalid frame length")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("WebSocket disconnected")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
