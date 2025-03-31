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
            # Save the uploaded file
            file_path = f"./tmp/{file.filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
            return {"message": "OK, question received with file", "question": question}
        else:
            return {"message": "OK, question received", "question": question}
    except Exception as ms: 
        return {"message": "OK, question received", "question": question,"error":ms}

# # Run the application
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
