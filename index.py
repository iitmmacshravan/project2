from fastapi import FastAPI, Form, HTTPException
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
import os

# Load PostgreSQL URL from environment variables
DATABASE_URL = "postgres://neondb_owner:npg_iEVqAj2oCLs0@ep-divine-truth-a5ir9ri7-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to PostgreSQL and create table if not exists
def create_table():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            sample_answer TEXT,
            code TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# Call function on startup
create_table()

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

@app.get("/view-data/")
async def view_data():
    """Fetches all records from the 'questions' table and returns them as a list."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM questions;")
        data = cur.fetchall()
        cur.close()
        conn.close()
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add-data/")
async def add_data(
    question: str = Form(...),
    sample_answer: str = Form(None),
    code: str = Form(None)
):
    """Adds a new record to the 'questions' table."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO questions (question, sample_answer, code) VALUES (%s, %s, %s) RETURNING id;",
            (question, sample_answer, code)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Data added successfully", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

