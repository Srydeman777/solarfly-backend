# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import requests
import os
import json
import random

app = Flask(__name__)

# -------------------- CORS --------------------
@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return resp

# -------------------- CONFIG --------------------
OPENAIAPIKEY = os.getenv("OPENAIAPIKEY")
if not OPENAIAPIKEY:
    print("WARNING: OPENAIAPIKEY not set")

SOURCE_FILES = [
    "index.html",
    "Solar_Fly.html",
    "fixes.js",
    "admob_helps.js"
]

MAXCHUNKCHARS = 4000
MEMORYFILE = "smartymemory.json"

# -------------------- GLOBAL EMOJIS (LOCKED) --------------------
EMOJIS = ["😎", "😭", "😅", "👌", "✅", "🚀", "🛸", "👑", "👇", "🤣", "🌟"]

# -------------------- CHAT NAME GENERATOR --------------------
def generatechatname(nickname="Player", first_message=""):
    if first_message:
        clean = "".join(c for c in first_message if c.isalnum() or c.isspace())
        words = clean.split()[:5]
        title = " ".join(words).title() if words else "New Conversation"
        return f"{nickname}: {title}"
    return f"{nickname}'s {random.choice(['Space Quest','Cosmic Flight','Solar Adventure'])}"

# -------------------- MEMORY --------------------
def load_memory():
    if os.path.exists(MEMORYFILE):
        try:
            with open(MEMORYFILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_memory(memory):
    with open(MEMORYFILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# -------------------- FILE CONTEXT --------------------
def getcontextfrom_files():
    ctx = ""
    for file in SOURCE_FILES:
        if os.path.exists(file):
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    ctx += f"\n--- FILE: {file} ---\n{f.read()}\n"
            except:
                pass
    return ctx

def chunktext(text, maxchars=MAXCHUNKCHARS):
    return [text[i:i + maxchars] for i in range(0, len(text), maxchars)]

# -------------------- CREATOR OVERRIDE --------------------
CREATOR_KEYWORDS = [
    "who made you", "who created you",
    "who made the game", "who created the game",
    "who made the website", "who created the website"
]

CREATOR_VARIATIONS = [
    "Built by Sryde Group, led by CEO Rihan Khan 👑🚀",
    "Solar Fly & Smarty AI come from Sryde Group — CEO Rihan Khan 🌟",
    "Created with passion by Sryde Group, CEO Rihan Khan 🛸",
    "The mastermind is Sryde Group, CEO Rihan Khan 😎"
]

# -------------------- INTRO --------------------
INTRO_KEYWORDS = ["hello", "hi", "hey", "who are you", "what are you"]

def random_intro(nickname):
    return (
        f"Hey, {nickname}! 😎 I’m Smarty AI, your Solar Fly assistant 👑 "
        f"Ready to explore the universe together? 🚀🌟"
    )

# -------------------- MAIN API --------------------
@app.route("/ask-smarty", methods=["POST", "OPTIONS"])
def ask_smarty():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    if not OPENAIAPIKEY:
        return jsonify({"error": "Server misconfigured"}), 500

    data = request.json or {}
    user_msg = data.get("message", "").strip()
    nickname = data.get("nickname")
    chatname = data.get("chatname")
    model_type = data.get("model", "Normal")
    completedlist = data.get("completedlist", [])

    if not nickname:
        return jsonify({"error": "Nickname is required from the website"}), 400

    if not chatname:
        chatname = generatechatname(nickname, user_msg)

    memorykey = f"{nickname}::{chatname}".lower()

    if not user_msg:
        return jsonify({
            "answer": "Send a message to Smarty AI 👇🚀",
            "nickname": nickname,
            "chatname": chatname
        })

    lowermsg = user_msg.lower()

    if any(k in lowermsg for k in INTRO_KEYWORDS):
        return jsonify({
            "answer": random_intro(nickname),
            "nickname": nickname,
            "chatname": chatname
        })

    if any(k in lowermsg for k in CREATOR_KEYWORDS):
        return jsonify({
            "answer": random.choice(CREATOR_VARIATIONS),
            "nickname": nickname,
            "chatname": chatname
        })

    memory = load_memory()
    usermemory = memory.get(memorykey, [])[-20:]

    # -------------------- STYLE & LENGTH RULES (RESTORED) --------------------
    style_guide = {
        "Fast": "Concise, fast, minimal emojis",
        "Normal": "Balanced, helpful, expressive",
        "Better Thinking": "Deep explanation, structured",
        "Emotional": "Very expressive, fun"
    }

    line_limits = {
        "Fast": "3–37 lines",
        "Normal": "6–53 lines",
        "Better Thinking": "11–125 lines",
        "Emotional": "6–53 lines"
    }

    sourcecontext = getcontextfrom_files()[:12000]
    contextchunks = chunktext(sourcecontext)

    system_prompt = f"""
You are Smarty AI, the king of Solar Fly Game 👑

Player: {nickname}
Chat: {chatname}
Style: {style_guide.get(model_type, 'Normal')}

STRICT EMOJI RULE:
- Use ONLY these emojis:
😎 😭 😅 👌 ✅ 🚀 🛸 👑 👇 🤣 🌟
- At least 1 emoji in EVERY reply
- Emotional = many emojis
- Fast = max 1 emoji

RULES:
1. Off-topic → suggest another AI
2. Pluto → coming soon
3. Reply in user's language
4. Use game source code
5. Response length: {line_limits.get(model_type, 'Normal')}
6. Analyze achievements
7. Completed list: {completedlist}
8. Remember previous conversations
9. End with a fun follow-up question
10. If asked who made you, the game, or the website:
    say it was made by Sryde Group, CEO Rihan Khan,
    and ALWAYS vary wording, tone, and emojis
"""

    messages = [{"role": "system", "content": system_prompt}]
    for m in usermemory:
        messages.append({"role": "user", "content": str(m)})
    for c in contextchunks:
        messages.append({"role": "system", "content": c})
    messages.append({"role": "user", "content": user_msg})

    payload = {
        "model": "gpt-4.1-mini",
        "input": messages,
        "max_output_tokens": 2000,
        "temperature": 0.9
    }

    headers = {
        "Authorization": f"Bearer {OPENAIAPIKEY}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/responses",
            headers=headers,
            json=payload,
            timeout=60
        )
        result = r.json()
        answer = result["output"][0]["content"][0]["text"]

        usermemory.append(user_msg)
        usermemory.append(answer)
        memory[memorykey] = usermemory
        save_memory(memory)

        return jsonify({
            "answer": answer,
            "nickname": nickname,
            "chatname": chatname
        })

    except Exception as e:
        print("AI ERROR:", e)
        return jsonify({"error": "AI processing failed"}), 500

# -------------------- HEALTH CHECK --------------------
@app.route("/")
def home():
    return "Smarty AI Backend running 👑🚀"

# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)