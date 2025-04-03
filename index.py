from fastapi import FastAPI, Form, HTTPException
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
import os
import openai
import numpy as np
import subprocess

# Load PostgreSQL URL from environment variables
DATABASE_URL = "postgres://neondb_owner:npg_iEVqAj2oCLs0@ep-divine-truth-a5ir9ri7-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
openai_api_base = "https://aiproxy.sanand.workers.dev/openai/v1"
openai_api_key = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIyZjIwMDAxNTlAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.RkyKH_Uh6PvjeJRDN7iRJTGTo_-YBe8BwbOk9CS--Os"

openai.api_key = openai_api_key
openai.api_base = openai_api_base
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)
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
def get_embedding(text: str):
    """Get OpenAI embedding for a given text."""
    response = openai.Embedding.create(input=text, model= "text-embedding-3-small")
    return np.array(response["data"][0]["embedding"])
def find_similar_question(question: str):
    """Find the most similar question in the database using OpenAI embeddings."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, question, sample_answer, code FROM questions;")
    records = cur.fetchall()
    cur.close()
    conn.close()
    
    question_embedding = get_embedding(question)
    
    best_match = None
    highest_similarity = -1
    
    for record in records:
        stored_embedding = get_embedding(record["question"])
        similarity = np.dot(question_embedding, stored_embedding) / (
            np.linalg.norm(question_embedding) * np.linalg.norm(stored_embedding)
        )
        
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = record
    print(highest_similarity if highest_similarity > 0.50 else None)
    return best_match if highest_similarity > 0.50 else None  # Threshold for similarity

def execute_code(code, timeout=120):
    temp_file_path = "/tmp/temp_script.py"  # Store file in Vercel's /tmp/ dir

    # Write the code to a temp file
    with open(temp_file_path, "w") as temp_file:
        temp_file.write(code)
    try:
        # Run the script with timeout
        result = subprocess.run(
            ["python3", temp_file_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout
        )
        print("Subprocess Python Version:", result.stdout)
        output = result.stdout if result.returncode == 0 else result.stderr
        ouput=output.strip()
    except subprocess.TimeoutExpired:
        output = "Execution timed out after 120 seconds."
    except Exception as e:
        output = f"An error occurred: {str(e)}"

    # Cleanup temp file
    # os.remove(temp_file_path)
    return output
@app.post("/api/")
async def process_question(question: str = Form(...), file: UploadFile = File(None)):
    try:
        file_path=None
        if True:
            # Save file in /tmp/ (Vercel allows writing only to /tmp/)
            if file:
                file_path = f"/tmp/{file.filename}"
                with open(file_path, "wb") as buffer:
                    buffer.write(await file.read())
        
            similar_question = find_similar_question(question)
        
            if similar_question:
                print(similar_question)
                if 'sql' in question.lower() or 'sql' in similar_question["question"].lower():
                    gpt_code=generate_new_sql_with_gpt(question, similar_question["question"], similar_question["code"], similar_question["sample_answer"],file_path)
                    cleaned_string = gpt_code.replace("```sql", "").replace("```", "").strip()
                    print(cleaned_string)
                    executed_output = cleaned_string
                else:
                    gpt_code=generate_new_code_with_gpt(question, similar_question["question"], similar_question["code"], similar_question["sample_answer"],file_path)
                    cleaned_string = gpt_code.replace("```python", "").replace("```", "").strip()
                    print(cleaned_string)
                    #executed_output = execute_code(similar_question["code"])
                    executed_output = execute_code(cleaned_string)
                print(executed_output)
                # return {
                #     "message": "Similar question found and executed.",
                #     "matched_question": similar_question["question"],
                #     "sample_answer": similar_question["sample_answer"],
                #     "execution_result": executed_output,
                # }
                return {
                    "answer" : executed_output.strip()
                }
            else:
                if 'sql' in question.lower():
                    gpt_code=generate_new_sql_with_gpt_for_unknown_qp(question,file_path)
                    cleaned_string = gpt_code.replace("```sql", "").replace("```", "").strip()
                    print(cleaned_string)
                    executed_output = cleaned_string
                else:
                    gpt_code=generate_new_code_with_gpt_for_unknown_qp(question,file_path)
                    cleaned_string = gpt_code.replace("```python", "").replace("```", "").strip()
                    print(cleaned_string)
                    executed_output = execute_code(cleaned_string)
                print(executed_output)
            #     return {
            #     "message": "OK, question received with file",
            #     "question": question,
            #     "file_path": file_path,
            #     "answer": executed_output
            # }
                return {
                "answer": executed_output.strip()
            }
        else:
            return {"message": "OK, question received", "question": question}

    except Exception as e:
        return {
            "message": "An error occurred",
            "question": question,
            "error": str(e)
        }

def generate_new_code_with_gpt_for_unknown_qp(question,file_path):
    prompt = f"""
    A user has asked a question: "{question}"
    also its file path is {file_path}
    if file path None then ignore it.
    Now, generate optimized Python code without any comments for the user's question and remember give only the code that prints the required result or give only the sql query if the user have requested for sql query.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # Change based on your available model
        messages=[{"role": "system", "content": "You are an expert Python coder."},
                  {"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]
def generate_new_code_with_gpt(question, reference_question,reference_code, reference_answer,file_path):
    prompt = f"""
    A user has asked a question: "{question}"
    
    Here is a similar question:{reference_question}
    reference_code:
    ``{reference_code}```
    
    And its corresponding sample output:
    "{reference_answer}"

    also its file path is {file_path}
    if file path None then ignore it.
    
    Now, generate optimized Python code without any comments for the user's question while using the reference as guidance and remember give only the code.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # Change based on your available model
        messages=[{"role": "system", "content": "You are an expert Python coder."},
                  {"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]
def generate_new_sql_with_gpt_for_unknown_qp(question,file_path):
    prompt = f"""
    A user has asked a question: "{question}"
    also its file path is {file_path}
    if file path None then ignore it.
    Now, generate optimized SQL Query for the user's question while using the reference as guidance and remember give only the Query.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # Change based on your available model
        messages=[{"role": "system", "content": "You are an expert Python coder."},
                  {"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]
def generate_new_sql_with_gpt(question, reference_question,reference_code, reference_answer,file_path):
    prompt = f"""
    A user has asked a question: "{question}"
    
    Here is a similar question:{reference_question}
    reference_query:
    ``{reference_code}```
    
    And its corresponding sample output:
    "{reference_answer}"

    also its file path is {file_path}
    if file path None then ignore it.
    
    Now, generate optimized SQL Query for the user's question while using the reference as guidance and remember give only the Query.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # Change based on your available model
        messages=[{"role": "system", "content": "You are an expert Python coder."},
                  {"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]
@app.delete("/delete-data/{id}/")
async def delete_data(id: int):
    """Deletes a record from the 'questions' table by ID."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM questions WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if deleted_id:
            return {"message": f"Record with ID {id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Record not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
