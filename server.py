# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# -------------------- CORS --------------------
@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return resp

# -------------------- CONFIG --------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment")

SOURCE_FILES = [
    "index.html",
    "Solar_Fly.html",
    "fixes.js",
    "admob_helps.js"
]

MAX_CHUNK_CHARS = 4000  # safe per request chunk


# -------------------- HELPER FUNCTIONS --------------------
def get_context_from_files():
    """Read all source files and return as a single string."""
    context = ""
    for file_path in SOURCE_FILES:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    data = f.read()
                    context += f"\n--- FILE: {file_path} ---\n{data}\n"
            except Exception as e:
                print("File read error:", file_path, e)
    return context


def chunk_text(text, max_chars=MAX_CHUNK_CHARS):
    """Split text into chunks to avoid token limit issues."""
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]


# -------------------- MAIN API --------------------
@app.route("/ask-smarty", methods=["POST"])
def ask_smarty():
    data = request.json or {}
    user_msg = data.get("message", "").strip()
    nickname = data.get("nickname", "Player")
    model_type = data.get("model", "Normal")
    completed_list = data.get("completed_list", [])

    if not user_msg:
        return jsonify({"answer": "Send a message to Smarty AI 🚀"})

    # Prepare system prompt
    style_guide = {
        "Fast": "Concise, fast, few emojis",
        "Better Thinking": "Deep explanation, minimal emojis",
        "Normal": "Balanced, helpful, emojis",
        "Emotional": "EXTREMELY expressive, 50+ emojis"
    }

    line_limits = {
        "Normal": "6-53 lines",
        "Better Thinking": "11-125 lines",
        "Fast": "3-24 lines",
        "Emotional": "6-53 lines"
    }

    source_context = get_context_from_files()
    context_chunks = chunk_text(source_context)

    system_prompt = f"""
You are Smarty AI, the king of Solar Fly Game.

Player: {nickname}
Style: {style_guide.get(model_type, 'Normal')}

RULES:
1. Off-topic -> tell user to use another AI
2. Pluto -> coming soon
3. Reply in user's language
4. Use game source code below
5. Response length: {line_limits.get(model_type, 'Normal')}
6. Analyze achievements
7. Completed list: {completed_list}
8. End with a fun follow-up question
"""

    # Merge user message with source code chunks
    messages = [{"role": "system", "content": system_prompt}]
    for chunk in context_chunks:
        messages.append({"role": "system", "content": chunk})
    messages.append({"role": "user", "content": user_msg})

    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": 2000  # safe limit
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        result = r.json()
        if "choices" in result:
            answer = result["choices"][0]["message"]["content"]
            return jsonify({"answer": answer})
        else:
            print("OpenAI Error:", result)
            return jsonify({"error": "Invalid response from AI provider"}), 500
    except Exception as e:
        print("AI ERROR:", e)
        return jsonify({"error": "AI processing failed"}), 500


# -------------------- HEALTH CHECK --------------------
@app.route("/")
def home():
    return "Smarty AI Backend is running 🚀"


# -------------------- LOCAL RUN --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)