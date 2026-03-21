from flask import Flask, request, jsonify, render_template
import os
import requests
import uuid

app = Flask(__name__)

# ================= API KEYS =================
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
SERP_API_KEY = os.environ.get("SERP_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
STOCK_API_KEY = os.environ.get("STOCK_API_KEY")

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

SYSTEM_PROMPT = (
    "You are Thinko, a brilliant AI assistant. "
    "Use the given live data properly and answer clearly."
)

users_chats = {}

# ================= SEARCH (SERP API) =================
def search_web(query):
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "q": query,
            "api_key": SERP_API_KEY,
            "num": 3
        }

        res = requests.get(url, params=params).json()

        results = []
        for item in res.get("organic_results", []):
            results.append(f"{item.get('title')} - {item.get('link')}")

        return "\n".join(results) if results else "No search results found."
    except:
        return "Search error"

# ================= NEWS (GNEWS) =================
def get_news():
    try:
        url = f"https://gnews.io/api/v4/search?q=india&lang=en&apikey={NEWS_API_KEY}"
        res = requests.get(url).json()

        articles = res.get("articles", [])
        if not articles:
            return "No latest news available"

        return "\n".join([a["title"] for a in articles[:3]])
    except:
        return "News error"

# ================= WEATHER (WEATHERAPI) =================
def get_weather(city="Chennai"):
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}"
        res = requests.get(url).json()

        temp = res["current"]["temp_c"]
        desc = res["current"]["condition"]["text"]

        return f"{city}: {temp}°C, {desc}"
    except:
        return "Weather error"

# ================= STOCK (ALPHA VANTAGE) =================
def get_stock(symbol="AAPL"):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={STOCK_API_KEY}"
        res = requests.get(url).json()

        price = res["Global Quote"]["05. price"]
        return f"{symbol} price: ${price}"
    except:
        return "Stock error"

# ================= ROUTES =================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/new_chat", methods=["POST"])
def new_chat():
    data = request.get_json(silent=True) or {}
    user_email = data.get("email")

    if not user_email:
        return jsonify({"error": "Email required"}), 400

    chat_id = str(uuid.uuid4())

    if user_email not in users_chats:
        users_chats[user_email] = {}

    users_chats[user_email][chat_id] = []

    return jsonify({"chat_id": chat_id})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}

    user_email = data.get("email")
    chat_id = data.get("chat_id")
    user_message = (data.get("message") or "").strip()

    if not user_email or not chat_id:
        return jsonify({"error": "Email and chat_id required"}), 400

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    if user_email not in users_chats:
        users_chats[user_email] = {}

    if chat_id not in users_chats[user_email]:
        users_chats[user_email][chat_id] = []

    chat_history = users_chats[user_email][chat_id]

    # ================= SMART API =================
    msg = user_message.lower()
    extra_context = ""

    if "weather" in msg or "temperature" in msg:
        extra_context = get_weather()

    elif "news" in msg:
        extra_context = get_news()

    elif "stock" in msg or "price" in msg:
        extra_context = get_stock()

    else:
        extra_context = search_web(user_message)

    # ================= AI =================
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history

    messages.append({
        "role": "user",
        "content": f"{user_message}\n\nLive Data:\n{extra_context}"
    })

    try:
        response = requests.post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {NVIDIA_API_KEY}"},
            json={
                "model": "meta/llama-3.1-70b-instruct",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024
            },
        )

        response.raise_for_status()
        ai_text = response.json()["choices"][0]["message"]["content"]

        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": ai_text})

        return jsonify({"response": ai_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_chats", methods=["GET"])
def get_chats():
    user_email = request.args.get("email")

    if not user_email:
        return jsonify({"error": "Email required"}), 400

    chat_ids = list(users_chats.get(user_email, {}).keys())
    return jsonify({"chat_ids": chat_ids})

@app.route("/get_messages", methods=["GET"])
def get_messages():
    user_email = request.args.get("email")
    chat_id = request.args.get("chat_id")

    if not user_email or not chat_id:
        return jsonify({"error": "Email and chat_id required"}), 400

    messages = users_chats.get(user_email, {}).get(chat_id, [])
    return jsonify({"messages": messages})

# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🧠 Thinko running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)
