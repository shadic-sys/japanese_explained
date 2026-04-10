from fastapi import FastAPI, UploadFile, File
import shutil
import os
from core import process_video

app = FastAPI()

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/process-video")
async def upload_video(video: UploadFile = File(...)):
    input_path = f"{UPLOAD_DIR}/{video.filename}"

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    result = process_video(input_path)

    return {
        "video_url": result["video"],
        "pdf_url": result["pdf"]
    }
