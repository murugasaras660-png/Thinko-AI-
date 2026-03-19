from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 🔥 Modes
MODES = {
    "explain": {
        "label": "💡 Concept Explainer",
        "system": "You are Thinko AI, an expert teacher. Explain clearly in simple terms."
    },
    "quiz": {
        "label": "🧠 Quiz Generator",
        "system": "You are Thinko AI. Generate 5 MCQ questions with answers."
    },
    "essay": {
        "label": "✍️ Essay Writer",
        "system": "You are Thinko AI. Write structured essays with intro, body, conclusion."
    }
}

# ✅ Home route
@app.route("/")
def index():
    first_mode = list(MODES.keys())[0]
    return render_template("index.html", modes=MODES, first_mode=first_mode)

# ✅ Chat route (NVIDIA AI)
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    mode = data.get("mode", "explain")
    user_message = data.get("message", "").strip()
    history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    api_key = os.getenv("NVIDIA_API_KEY")

    if not api_key:
        return jsonify({"error": "NVIDIA API key not set"}), 500

    # 🔥 Messages format
    messages = [{"role": "system", "content": MODES[mode]["system"]}]

    for h in history:
        messages.append({
            "role": h["role"],
            "content": h["content"]
        })

    messages.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta/llama-3.1-70b-instruct",
                "messages": messages,
                "max_tokens": 700,
                "temperature": 0.7
            }
        )

        result = response.json()

        ai_reply = result["choices"][0]["message"]["content"]

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Run server
if __name__ == "__main__":
    print("🚀 Thinko AI running at http://127.0.0.1:5000")
    app.run(debug=True)
