import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, make_response, jsonify

app = Flask(__name__)
STORY_DIR = "stories"
os.makedirs(STORY_DIR, exist_ok=True)

API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-your-key")

def load_story(story_id):
    path = os.path.join(STORY_DIR, f"{story_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"title": "", "mode": "game", "steps": 0, "history": [], "log": []}

def save_story(story_id, data):
    with open(os.path.join(STORY_DIR, f"{story_id}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_from_deepseek(prompt, max_tokens=800):
    import requests
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": max_tokens
    }
    res = requests.post(url, headers=headers, json=data)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"].strip()

@app.route('/')
def index():
    stories = []
    for fname in os.listdir(STORY_DIR):
        sid = fname.replace(".json", "")
        data = load_story(sid)
        stories.append({"id": sid, "title": data.get("title", "无标题"), "steps": data.get("steps", 0)})
    return render_template("index.html", stories=stories)

@app.route('/create', methods=['POST'])
def create():
    title = request.form.get("title", "无标题")
    background = request.form.get("background", "")
    story_id = str(uuid.uuid4())[:8]
    data = {
        "title": title,
        "mode": "game",
        "steps": 0,
        "history": [],
        "log": [{"type": "background", "text": background}]
    }
    save_story(story_id, data)
    return redirect(url_for("play", story_id=story_id))

@app.route('/play/<story_id>', methods=['GET', 'POST'])
def play(story_id):
    data = load_story(story_id)

    if request.method == 'POST':
        choice = request.form.get("choice", "").strip()
        if choice:
            data["log"].append({"type": "choice", "text": choice})
            data["steps"] += 1

        history_text = "
".join([item["text"] for item in data["log"] if item["type"] in ["background", "story", "choice"]])

        if data["steps"] >= 50:
            prompt = f"你是一位互动小说引擎，现在已进行第 {data['steps']} 次选择。

当前剧情（摘要）：
{history_text}

请生成该故事的结局段落，解决所有人物关系和冲突，风格保持一致。不要再生成选项。"
        else:
            prompt = f"{history_text}

请生成：
1. 一段新的剧情推进（200字内）
2. 接下来的三个选择（A/B/C），以选项开头。"

        try:
            output = generate_from_deepseek(prompt, 800)
        except Exception as e:
            return f"生成失败：{str(e)}", 500

        data["log"].append({"type": "story", "text": output})
        save_story(story_id, data)
        return redirect(url_for("play", story_id=story_id))

    return render_template("play.html", story_id=story_id, data=load_story(story_id))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
