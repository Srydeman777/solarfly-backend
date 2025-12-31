# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import requests, os, json, random, base64, tempfile, pathlib, mimetypes

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
PORT = int(os.getenv("PORT", 5000))
SOURCE_FILES = ["index.html","Solar_Fly.html","fixes.js","admob_helps.js"]
MAXCHUNKCHARS = 4000
MEMORYFILE = "smartymemory.json"

# -------------------- GLOBAL EMOJIS --------------------
EMOJIS = ["😎","😭","😅","👌","✅","🚀","🛸","👑","👇","🤣","🌟"]

# -------------------- CHAT NAME --------------------
def generatechatname(nickname, first_message):
    clean = "".join(c for c in first_message if c.isalnum() or c.isspace())
    words = clean.split()[:5]
    title = " ".join(words).title() if words else "New Conversation"
    return f"{nickname}: {title}"

# -------------------- MEMORY --------------------
def load_memory():
    if os.path.exists(MEMORYFILE):
        try:
            with open(MEMORYFILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_memory(memory):
    with open(MEMORYFILE,"w",encoding="utf-8") as f:
        json.dump(memory,f,ensure_ascii=False,indent=2)

# -------------------- FILE CONTEXT --------------------
def getcontextfrom_files():
    ctx=""
    for file in SOURCE_FILES:
        if os.path.exists(file):
            try:
                with open(file,"r",encoding="utf-8",errors="ignore") as f:
                    # ✅ BUG FIXED HERE (nothing else changed)
                    ctx += f"\n--- FILE: {file} ---\n{f.read()}"
            except:
                pass
    return ctx

def chunktext(text,maxchars=MAXCHUNKCHARS):
    return [text[i:i+maxchars] for i in range(0,len(text),maxchars)]

# -------------------- CREATOR & INTRO --------------------
CREATOR_KEYWORDS = [
    "who made you","who created you","who made the game",
    "who created the game","who made the website","who created the website"
]

CREATOR_VARIATIONS = [
    "Built by Sryde Group, led by CEO Rihan Khan 👑🚀",
    "Solar Fly & Smarty AI come from Sryde Group — CEO Rihan Khan 🌟",
    "Created with passion by Sryde Group, CEO Rihan Khan 🛸",
    "The mastermind is Sryde Group, CEO Rihan Khan 😎"
]

INTRO_KEYWORDS = ["hello","hi","hey","who are you","what are you"]

def random_intro(nickname):
    return f"Hey, {nickname}! 😎 I’m Smarty AI, your Solar Fly assistant 👑 Ready to explore the universe together? 🚀🌟"

# -------------------- IMAGE HELPERS --------------------
def guess_mime_from_filename(filename):
    if not filename: return None
    mime,_=mimetypes.guess_type(filename)
    return mime

def parse_base64_data(b64_input):
    if not b64_input: return None,None
    if b64_input.startswith("data:"):
        try:
            header,b64data = b64_input.split(",",1)
            mime = header.split(";")[0].replace("data:","")
            return mime,b64data
        except: return None,None
    else: return None,b64_input

def save_temp_image(b64_data,mime,filename_hint="image"):
    suffix=""
    if mime: suffix=mimetypes.guess_extension(mime) or ""
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=suffix,prefix=filename_hint+"_")
    try:
        tmp.write(base64.b64decode(b64_data))
        tmp.flush(); tmp.close()
        return tmp.name
    except:
        try: tmp.close()
        except: pass
        return None

# -------------------- MAIN API --------------------
@app.route("/ask-smarty",methods=["POST","OPTIONS"])
def ask_smarty():
    if request.method=="OPTIONS": return jsonify({}),200
    if not OPENAIAPIKEY: return jsonify({"error":"Server misconfigured"}),500

    data=request.json or {}
    user_msg=(data.get("message") or "").strip()
    nickname=data.get("nickname")
    chatname=data.get("chatname")
    model_type=data.get("model","Normal")
    completedlist=data.get("completedlist",[])

    # Image inputs
    image_base64 = data.get("image_base64")
    image_filename = data.get("image_filename")
    image_mime = data.get("image_mime")
    image_url = data.get("image_url")

    if not nickname: return jsonify({"error":"Nickname required"}),400

    # Chat name
    if not chatname and user_msg: chatname = generatechatname(nickname,user_msg)
    if not chatname: chatname=f"{nickname}: New Conversation"
    memorykey=f"{nickname}::{chatname}".lower()

    if not user_msg and not (image_base64 or image_url):
        return jsonify({"answer":"Send a message or image to Smarty AI 👇🚀","nickname":nickname,"chatname":chatname})

    lowermsg=(user_msg or "").lower()
    if user_msg and any(k in lowermsg for k in INTRO_KEYWORDS):
        return jsonify({"answer":random_intro(nickname),"nickname":nickname,"chatname":chatname})
    if user_msg and any(k in lowermsg for k in CREATOR_KEYWORDS):
        return jsonify({"answer":random.choice(CREATOR_VARIATIONS),"nickname":nickname,"chatname":chatname})

    memory = load_memory()
    usermemory = memory.get(memorykey,[])[-20:]

    style_guide = {"Fast":"Concise, fast, minimal emojis","Normal":"Balanced, helpful, expressive","Better Thinking":"Deep explanation, structured","Emotional":"Very expressive, fun"}
    line_limits = {"Fast":"3–24 lines","Normal":"6–53 lines","Better Thinking":"11–125 lines","Emotional":"6–53 lines"}

    sourcecontext=getcontextfrom_files()[:12000]
    contextchunks=chunktext(sourcecontext)

    system_prompt=f"""
You are Smarty AI, the king of Solar Fly Game 👑
Player: {nickname}
Chat: {chatname}
Style: {style_guide.get(model_type,'Normal')}

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
5. Response length: {line_limits.get(model_type,'Normal')}
6. Analyze achievements
7. Completed list: {completedlist}
8. Remember previous conversations
9. End with a fun follow-up question
10. If asked who made you, the game, or the website:
    say it was made by Sryde Group, CEO Rihan Khan,
    and ALWAYS vary wording, tone, and emojis
"""

    messages=[{"role":"system","content":system_prompt}]
    for m in usermemory: messages.append({"role":"user","content":str(m)})
    for c in contextchunks: messages.append({"role":"system","content":c})

    # -------------------- IMAGE HANDLING --------------------
    attached_image_data_uri=None
    saved_temp_path=None
    try:
        if image_url: attached_image_data_uri=image_url
        elif image_base64:
            mime,b64data=parse_base64_data(image_base64)
            if not mime: mime=image_mime or guess_mime_from_filename(image_filename) or "image/png"
            if not b64data: return jsonify({"error":"Invalid base64 image data"}),400
            saved_temp_path=save_temp_image(b64data,mime,filename_hint=(pathlib.Path(image_filename).stem if image_filename else "upload"))
            attached_image_data_uri=f"data:{mime};base64,{b64data}"
    except: attached_image_data_uri=None; saved_temp_path=None

    if attached_image_data_uri:
        user_content=[]
        if user_msg: user_content.append({"type":"input_text","text":user_msg})
        user_content.append({"type":"input_image","image_url":attached_image_data_uri})
        messages.append({"role":"user","content":user_content})
    else:
        messages.append({"role":"user","content":user_msg})

    payload={"model":"gpt-4.1-mini","input":messages,"max_output_tokens":2000,"temperature":0.9}
    headers={"Authorization":f"Bearer {OPENAIAPIKEY}","Content-Type":"application/json"}

    try:
        r=requests.post("https://api.openai.com/v1/responses",headers=headers,json=payload,timeout=60)
        result=r.json()
        answer=""
        try: answer=result["output"][0]["content"][0].get("text","")
        except:
            try:
                blocks=result.get("output",[])
                texts=[]
                for b in blocks:
                    for c in b.get("content",[]):
                        if isinstance(c,dict) and "text" in c: texts.append(c["text"])
                        elif isinstance(c,str): texts.append(c)
                answer="\n".join([t for t in texts if t])
            except: answer=str(result)

        usermemory.append(user_msg)
        if attached_image_data_uri:
            img_note=f"[image attached: {image_filename or 'user_image'} saved_at={saved_temp_path or 'n/a'} url={attached_image_data_uri if image_url else 'data-uri'}]"
            usermemory.append(img_note)
            usermemory.append(answer)
        else:
            usermemory.append(answer)

        memory[memorykey]=usermemory
        save_memory(memory)
        return jsonify({"answer":answer,"nickname":nickname,"chatname":chatname})

    except Exception as e:
        print("AI ERROR:",e)
        return jsonify({"error":"AI processing failed","details":str(e)}),500

# -------------------- HEALTH CHECK --------------------
@app.route("/")
def home():
    return "Smarty AI Backend running 👑🚀"

# -------------------- RUN --------------------
if __name__=="__main__":
    app.run(host="0.0.0.0",port=PORT)