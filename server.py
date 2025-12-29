# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import requests
import os
import base64

app = Flask(__name__)

# -------------------- CORS (manual, safe) --------------------
@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return resp


# -------------------- CONFIG --------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SOURCE_FILES = [
    "index.html",
    "Solar_Fly.html",
    "fixes.js",
    "admob_helps.js"
]

MAX_CONTEXT_CHARS = 12000  # safe limit to avoid token overflow


# -------------------- FILE CONTEXT --------------------
def get_context_from_files():
    context = ""
    for file_path in SOURCE_FILES:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    data = f.read()
                    if len(context) + len(data) > MAX_CONTEXT_CHARS:
                        break
                    context += f"\n--- FILE: {file_path} ---\n{data}\n"
            except Exception as e:
                print("File read error:", file_path, e)
    return context


# -------------------- MAIN API --------------------
@app.route("/ask-smarty", methods=["POST"])
def ask_smarty():
    data = request.json or {}

    user_msg = data.get("message", "").strip()
    nickname = data.get("nickname", "Player")
    model_type = data.get("model", "Normal")
    images_base64 = data.get("images", [])
    image_mimes = data.get("image_types", [])
    completed_list = data.get("completed_list", [])

    if not user_msg and not images_base64:
        return jsonify({"answer": "Send a message or screenshot(s) 📷"})

    source_context = get_context_from_files()

    line_limits = {
        "Normal": "6-53 lines",
        "Better Thinking": "11-125 lines",
        "Fast": "3-24 lines",
        "Emotional": "6-53 lines"
    }

    style_guide = {
        "Fast": "Concise, fast, few emojis 😊",
        "Better Thinking": "Deep explanation, minimal emojis 🤔",
        "Normal": "Balanced, helpful, emojis 😎",
        "Emotional": "EXTREMELY expressive, 50+ emojis 🤩🤯"
    }

    system_prompt = f"""
You are Smarty AI 😎, the king of Solar Fly Game.

Player: {nickname}
Style: {style_guide.get(model_type)}

RULES:
1. Off-topic → tell user to use another AI
2. Pluto → coming soon
3. Reply in user's language
4. Use game source code below
5. Response length: {line_limits.get(model_type)}
6. Analyze screenshots & achievements
7. Completed list: {completed_list}
8. End with a fun follow-up question

GAME SOURCE:
{source_context}
"""

    content = []

    if user_msg:
        content.append({"type": "text", "text": user_msg})

    for i, img in enumerate(images_base64):
        mime = image_mimes[i] if i < len(image_mimes) else "image/jpeg"
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime};base64,{img}"
            }
        })

    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ],
        "max_tokens": 1600
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
        answer = result["choices"][0]["message"]["content"]
        return jsonify({"answer": answer})

    except Exception as e:
        print("AI ERROR:", e)
        return jsonify({"error": "AI processing failed"}), 500


# -------------------- HEALTH CHECK --------------------
@app.route("/")
def home():
    return "Smarty AI Backend is running ✅"


# -------------------- LOCAL RUN --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)