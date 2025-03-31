from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/api/")
async def process_question(question: str = Form(...), file: UploadFile = File(None)):
    try:
        if file:
            # Save file in /tmp/ (Vercel allows writing only to /tmp/)
            file_path = f"/tmp/{file.filename}"
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())

            return {
                "message": "OK, question received with file",
                "question": question,
                "file_path": file_path
            }
        else:
            return {"message": "OK, question received", "question": question}

    except Exception as e:
        return {
            "message": "An error occurred",
            "question": question,
            "error": str(e)
        }
