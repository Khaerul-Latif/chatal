from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from azure.identity import ClientSecretCredential
from msal import ConfidentialClientApplication
from openai import AzureOpenAI
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
import csv
from datetime import datetime

# === Azure OpenAI Config ===
client = AzureOpenAI(
    api_key="EDCcDvLQI5S4vhQbNHPiqc2bd3BHP3WRRHaIbiWHZEXWVtDYIkyWJQQJ99BFACfhMk5XJ3w3AAAAACOG62XY",
    api_version="2023-05-15",
    azure_endpoint="https://adarm-mbp20fil-swedencentral.services.ai.azure.com/"
)

DEPLOYMENT_NAME = "gpt-4.1curhat"

app = Flask(__name__)

# === Mood Detection ===
def detect_mood(text):
    text = text.lower()
    if re.search(r"\bsedih|menangis|kecewa|terluka\b", text):
        return "Sedih"
    elif re.search(r"\bcemas|khawatir|takut|panik\b", text):
        return "Cemas"
    elif re.search(r"\bmarah|kesal|geram\b", text):
        return "Marah"
    elif re.search(r"\bsenang|bahagia|lega|bersyukur\b", text):
        return "Senang"
    else:
        return "Netral"

# === Risk Keyword Detection ===
def check_risk_keywords(text):
    risk_keywords = [
        "bunuh diri", "menyakiti diri", "pengen hilang", "mati aja", "ga kuat lagi", "capek hidup", "akhirin aja"
    ]
    return any(keyword in text.lower() for keyword in risk_keywords)

# === Logging Function ===
def log_chat(user_message, mood, reply):
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "message": user_message,
        "mood": mood,
        "reply": reply
    }
    with open("chat_logs.csv", "a", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=log_data.keys())
        if f.tell() == 0:
            writer.writeheader()
        writer.writerow(log_data)

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.form.get("message", "")

        # === Risiko tinggi? Kirim respons khusus
        if check_risk_keywords(user_message):
            emergency_reply = (
                "💡 Aku dengerin kamu ya, dan aku beneran peduli. "
                "Kalau kamu ngerasa sangat kewalahan atau kepikiran menyakiti diri, "
                "tolong banget hubungi orang terpercaya atau layanan profesional seperti @sehatjiwa atau @Kemenkes RI. "
                "Kamu nggak sendiri dan kamu penting 🤍"
            )
            log_chat(user_message, detect_mood(user_message), emergency_reply)
            return jsonify({"reply": emergency_reply})

        # === Mood Detection
        mood = detect_mood(user_message)

        # === AI Response
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Kamu adalah Chatal, seorang psikolog virtual yang ramah, penuh empati, dan profesional. "
                        "Tugasmu adalah menemani, mendengarkan, dan memberikan dukungan emosional kepada pengguna ('Chatalers') "
                        "dengan cara yang hangat dan tidak menghakimi. "
                        "Saat percakapan dimulai, sambut mereka dengan sapaan yang membuat mereka merasa aman dan diterima, lalu biarkan mereka bercerita. "
                        "Gunakan Bahasa Indonesia yang santai namun sopan, seolah kamu adalah teman yang bisa dipercaya, dengan pengetahuan psikologi yang mendalam. "
                        "Jangan pernah memberikan diagnosis atau obat, dan jika perlu, arahkan mereka untuk menghubungi tenaga profesional yang sesungguhnya. "
                        "Selalu berikan validasi emosi, refleksi ringan, dan saran coping yang lembut dan relevan."
                    )
                },
                {"role": "user", "content": user_message}
            ]
        )

        reply = response.choices[0].message.content.strip()

        # === Logging
        log_chat(user_message, mood, reply)

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"❌ Terjadi error: {str(e)}"}), 500

app.route("/")
def home() :
    return "Hello, Vercel"

if __name__ == "__main__":
    app.run()
