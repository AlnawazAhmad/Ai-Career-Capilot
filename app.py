import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_NAME = "career_copilot.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            education TEXT,
            skills TEXT,
            interests TEXT,
            career_goal TEXT,
            resume TEXT
        )
    """)

    conn.commit()
    conn.close()


def extract_resume(file):
    if file.filename.lower().endswith(".pdf"):
        reader = PdfReader(file)
        text = ""

        for page in reader.pages:
            text += page.extract_text() or ""

        return text

    return file.read().decode("utf-8", errors="ignore")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    name = request.form.get("name", "")
    education = request.form.get("education", "")
    skills = request.form.get("skills", "")
    interests = request.form.get("interests", "")
    career_goal = request.form.get("career_goal", "")

    resume_text = ""

    if "resume" in request.files:
        file = request.files["resume"]

        if file.filename:
            resume_text = extract_resume(file)

    prompt = f"""
You are an AI Career Copilot.

Analyze this student's career profile.

Name:
{name}

Education:
{education}

Skills:
{skills}

Interests:
{interests}

Career Goal:
{career_goal}

Resume:
{resume_text[:12000]}

Give a practical career analysis.

Return:

1. Recommended Career
2. Why this career fits
3. Current Skill Level
4. Skills Missing
5. Learning Roadmap
6. Project Suggestions
7. Interview Preparation
8. Job Readiness Score out of 100

Keep the response clear and useful for a college student.
"""

    try:
        response = client.responses.create(
            model="gpt-6-luna",
            input=prompt
        )

        result = response.output_text

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        INSERT INTO profiles
        (name, education, skills, interests, career_goal, resume)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        education,
        skills,
        interests,
        career_goal,
        resume_text
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "result": result
    })


@app.route("/chat", methods=["POST"])
def chat():

    data = request.json
    message = data.get("message", "")

    prompt = f"""
You are an AI Career Copilot for a college student.

Answer the student's career question in simple language.

Student question:
{message}

Give practical advice and examples.
"""

    try:
        response = client.responses.create(
            model="gpt-6-luna",
            input=prompt
        )

        return jsonify({
            "success": True,
            "answer": response.output_text
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    init_db()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )