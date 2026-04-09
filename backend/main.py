import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple

import requests
from flask import jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import desc

from analytics import EmotionAnalytics
from database import create_app
from models import Conversation, UserFeedback, db


# =========================================================
# CONFIG
# =========================================================

# Change this to False only if you want to force fallback mode
ENABLE_LLM = True
OLLAMA_MODEL = "phi3:mini"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

print("ENABLE_LLM =", ENABLE_LLM)
print("OLLAMA_MODEL =", OLLAMA_MODEL)

app = create_app()
CORS(app)

analytics = EmotionAnalytics(
    exports_dir=os.path.join(os.path.dirname(__file__), "exports")
)


# =========================================================
# RULES
# =========================================================

EMOTION_RULES = {
    "joy": {
        "keywords": [
            "happy", "great", "amazing", "awesome", "excited",
            "love", "glad", "relieved", "good", "wonderful", "proud"
        ],
        "weight": 1.0,
    },
    "sadness": {
        "keywords": [
            "sad", "upset", "depressed", "cry", "lonely",
            "hurt", "broken", "down", "unhappy", "tired", "low"
        ],
        "weight": 1.2,
    },
    "anger": {
        "keywords": [
            "angry", "mad", "hate", "annoyed", "furious",
            "irritated", "frustrated", "frustrating", "worst"
        ],
        "weight": 1.3,
    },
    "fear": {
        "keywords": [
            "fear", "afraid", "scared", "terrified",
            "panic", "unsafe", "frightened"
        ],
        "weight": 1.25,
    },
    "anxiety": {
        "keywords": [
            "anxious", "worried", "stress", "stressed",
            "nervous", "overthinking", "pressure", "tense"
        ],
        "weight": 1.2,
    },
        "love": {
        "keywords": [
            "love", "in love", "crush", "romantic",
            "feelings", "like someone", "special someone",
            "heart", "falling for"
        ],
        "weight": 1.4,
    },
    "confusion": {
        "keywords": [
            "confused", "unclear", "understand", "lost",
            "doubt", "not sure", "why", "how"
        ],
        "weight": 0.9,
    },
}

INTENT_RULES = {
    "greeting": ["hello", "hi", "hey", "good morning", "good evening"],
    "farewell": ["bye", "goodbye", "see you", "take care"],
    "support": ["help me", "i feel", "i am feeling", "support", "comfort me", "listen to me"],
    "advice": ["what should i do", "advise", "suggest", "guide", "recommend", "give me advice","how to express", "how to tell", "how do i say", "confess"],
    "information": ["what is", "explain", "tell me", "define", "how does", "how to", "can you explain"],
    "complaint": ["not working", "issue", "problem", "wrong", "bad", "hate this", "failed", "error"],
    "request": ["can you", "could you", "please", "i need", "i want", "do this"],
    "gratitude": ["thanks", "thank you", "appreciate", "helped a lot"],
}

NEGATIONS = {"not", "don't", "never", "no", "isn't", "wasn't", "can't"}
QUESTION_WORDS = {"what", "why", "how", "when", "where", "which", "who"}


# =========================================================
# REASONER
# =========================================================

class ConversationReasoner:
    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return re.findall(r"[a-zA-Z']+", text.lower())

    @staticmethod
    def infer_need(emotion: str, intent: str) -> str:
        if emotion in {"sadness", "fear", "anxiety"}:
            return "reassurance"
        if emotion == "anger":
            return "de-escalation"
        if intent in {"information", "request"}:
            return "clarity"
        if intent == "advice":
            return "guidance"
        return "conversation"

    @classmethod
    def detect_emotion_and_intent(
        cls,
        message: str,
        history: List[Conversation]
    ) -> Tuple[Dict[str, float], str, str, List[str]]:
        text = cls.normalize(message)
        tokens = cls.tokenize(text)
        token_set = set(tokens)

        emotion_scores = defaultdict(float)
        reasoning: List[str] = []

        exclamations = message.count("!")
        question_marks = message.count("?")
        has_negation = any(t in NEGATIONS for t in tokens)

        # keyword scoring
        for emotion, config in EMOTION_RULES.items():
            for kw in config["keywords"]:
                if kw in text:
                    emotion_scores[emotion] += config["weight"]

        # heuristics
        if exclamations >= 2:
            emotion_scores["anger"] += 0.5
            emotion_scores["joy"] += 0.3
            reasoning.append("High punctuation intensity detected.")

        if question_marks >= 2 or "not sure" in text:
            emotion_scores["confusion"] += 0.6
            reasoning.append("Repeated questioning suggests confusion.")

        if has_negation and any(word in token_set for word in ["happy", "fine", "good", "okay"]):
            emotion_scores["sadness"] += 0.8
            reasoning.append("Negative phrasing around positive words detected.")

        # carry-over from previous turn
        if history:
            last_emotion = history[-1].emotion_primary or "neutral"
            if last_emotion in {"sadness", "anger", "anxiety", "fear"} and any(
                word in token_set for word in ["still", "again", "same"]
            ):
                emotion_scores[last_emotion] += 0.7
                reasoning.append(f"Emotion carried forward from previous turn: {last_emotion}")

        primary_emotion = "neutral"
        intensity = 0.2

        if emotion_scores:
            primary_emotion = max(emotion_scores, key=emotion_scores.get)
            top_score = emotion_scores[primary_emotion]
            intensity = min(1.0, 0.25 + (top_score * 0.18))

        sentiment_map = {
            "joy": 0.85,
            "love": 0.9,
            "sadness": -0.75,
            "anger": -0.9,
            "fear": -0.7,
            "anxiety": -0.65,
            "confusion": -0.25,
            "neutral": 0.0,
        }
        sentiment = sentiment_map.get(primary_emotion, 0.0)

        intent_scores = defaultdict(float)
        for intent, patterns in INTENT_RULES.items():
            for pattern in patterns:
                if pattern in text:
                    intent_scores[intent] += 1.2 if " " in pattern else 1.0

        if tokens and tokens[0] in QUESTION_WORDS:
            intent_scores["information"] += 0.8

        if "?" in message and any(p in text for p in ["can you", "could you", "please", "i need"]):
            intent_scores["request"] += 1.0

        if any(w in text for w in ["error", "crash", "bug", "failed"]):
            intent_scores["complaint"] += 1.1

        if primary_emotion in {"sadness", "anxiety", "fear"}:
            intent_scores["support"] += 0.6

        intent = max(intent_scores, key=intent_scores.get) if intent_scores else "general"
        needs = cls.infer_need(primary_emotion, intent)

        reasoning.append(f"Emotion={primary_emotion}, Intent={intent}, Need={needs}")

        emotion_data = {
            "primary": primary_emotion,
            "intensity": round(float(intensity), 2),
            "sentiment": sentiment,
        }

        return emotion_data, intent, needs, reasoning


# =========================================================
# HELPERS
# =========================================================

def get_recent_context(session_id: str, limit: int = 5) -> List[Conversation]:
    if not session_id:
        return []

    rows = (
        Conversation.query
        .filter_by(session_id=session_id)
        .order_by(desc(Conversation.timestamp))
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


def format_context(history: List[Conversation]) -> str:
    if not history:
        return "No prior context."

    lines = []
    for item in history[-5:]:
        lines.append(
            f"User: {item.user_message}\n"
            f"Assistant: {item.bot_response}\n"
            f"Emotion: {item.emotion_primary}, Intent: {item.intent}"
        )
    return "\n---\n".join(lines)


def call_ollama(prompt: str):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=180
        )

        print("Ollama status code:", response.status_code)
        print("Ollama raw response:", response.text[:500])

        if response.status_code != 200:
            return None

        data = response.json()
        return data.get("response", None)

    except Exception as e:
        print("Ollama error:", e)
        return None


def build_fallback_reply(message: str, emotion: str, intent: str, needs: str) -> str:
    msg = message.lower()

    if intent == "greeting":
        return "Hello. How are you feeling today?"

    if intent == "advice" and emotion == "love":
        return "If you want to express love, keep it simple, honest, and personal. Speak naturally about what you feel instead of trying to impress."

    if emotion == "love":
        return "That sounds genuine and meaningful. If you want to express your feelings, start simply and honestly instead of trying to sound perfect."

    if emotion == "sadness" or "low" in msg:
        return "I am sorry you're feeling low. Do you want to talk about what is bothering you?"

    if emotion == "anxiety":
        return "You seem stressed. Try to focus on one problem at a time instead of everything at once."

    if emotion == "anger":
        return "You sound frustrated. Slow down and tell me the exact problem so I can help properly."

    if intent == "support":
        return "I am here with you. Tell me a little more so I can respond better."

    if intent == "request":
        return "Sure. Tell me exactly what help you need."

    if intent == "information":
        return "Ask your question directly and I will explain it clearly."

    return "I understand. Can you explain a bit more so I can help properly?"

def generate_bot_response(message: str, emotion: str, intent: str, needs: str, session_id: str = None):
    history = get_recent_context(session_id) if session_id else []
    context_text = format_context(history)

    prompt = f"""
You are an intelligent conversational AI focused on emotional understanding.

Recent conversation context:
{context_text}

Current user message: {message}
Detected emotion: {emotion}
Detected intent: {intent}
Detected need: {needs}

Rules:
- Respond naturally, warmly, and like a real supportive assistant.
- If the user message is about love, relationships, confusion, sadness, anxiety, or feelings, respond with emotional intelligence.
- If the user is asking for advice, give practical and specific guidance.
- Avoid robotic, generic, or overly formal replies.
- Keep the reply to 3 to 5 lines.
- Do not mention labels like emotion, intent, or need in the reply.
"""

    if ENABLE_LLM:
        llm_reply = call_ollama(prompt)
        if llm_reply and llm_reply.strip():
            return llm_reply.strip(), OLLAMA_MODEL

    fallback_reply = build_fallback_reply(message, emotion, intent, needs)
    return fallback_reply, "fallback-rule-engine"


# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "llm_enabled": ENABLE_LLM, "model": OLLAMA_MODEL})


@app.route("/test-ollama")
def test_ollama():
    if not ENABLE_LLM:
        return jsonify({"reply": None, "message": "LLM disabled"})
    reply = call_ollama("Say hello in one short sentence.")
    return jsonify({"reply": reply})


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}

        message = (data.get("message") or "").strip()
        session_id = data.get("session_id", "default")

        if not message:
            return jsonify({"error": "Message is required"}), 400

        history = get_recent_context(session_id)

        # analysis
        try:
            emotion_data, intent, needs, reasoning = ConversationReasoner.detect_emotion_and_intent(
                message, history
            )
            emotion = emotion_data.get("primary", "neutral")
            intensity = emotion_data.get("intensity", 0.2)
            sentiment = emotion_data.get("sentiment", 0.0)
            print("MESSAGE =", message)
            print("SESSION =", session_id)
            print("EMOTION =", emotion)
            print("INTENT =", intent)
            print("NEEDS =", needs)
        except Exception as e:
            print("Analysis error:", e)
            emotion = "neutral"
            intensity = 0.2
            sentiment = 0.0
            intent = "general"
            needs = "conversation"
            reasoning = ["Fallback analysis used due to internal analysis error."]

        # response generation
        try:
            bot_response, response_source = generate_bot_response(
                message,
                emotion,
                intent,
                needs,
                session_id=session_id
            )
        except Exception as e:
            print("Response generation error:", e)
            bot_response = "Sorry, something went wrong. Please try again."
            response_source = "error-fallback"

        # save to database
        conversation_id = None
        try:
            conversation = Conversation(
                session_id=session_id,
                user_message=message,
                bot_response=bot_response,
                emotion_primary=emotion,
                emotion_intensity=float(intensity),
                sentiment_score=float(sentiment),
                intent=intent,
                response_source=response_source,
            )
            db.session.add(conversation)
            db.session.commit()
            conversation_id = conversation.id
        except Exception as e:
            print("Database save error:", e)
            db.session.rollback()

        return jsonify({
            "conversation_id": conversation_id,
            "session_id": session_id,
            "response": bot_response,
            "emotion": emotion,
            "intent": intent,
            "needs": needs,
            "reasoning_summary": reasoning,
            "response_source": response_source
        })

    except Exception as e:
        print("Chat API error:", e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/analytics/summary/<session_id>")
def analytics_summary(session_id):
    summary = analytics.get_session_summary(session_id)
    if not summary:
        return jsonify({"error": "No session found"}), 404
    return jsonify(summary)


@app.route("/analytics/heatmap/<session_id>")
def analytics_heatmap(session_id):
    filename = analytics.generate_emotion_heatmap(session_id=session_id)
    if not filename:
        return jsonify({"error": "Need at least 2 messages to generate heatmap"}), 400
    return jsonify({"heatmap_url": f"/exports/{filename}"})


@app.route("/analytics/export-csv/<session_id>")
def analytics_export_csv(session_id):
    filename = analytics.export_session_csv(session_id)
    if not filename:
        return jsonify({"error": "No session found"}), 404
    return send_from_directory(analytics.exports_dir, filename, as_attachment=True)


@app.route("/exports/<path:filename>")
def exports(filename):
    return send_from_directory(analytics.exports_dir, filename)


@app.route("/feedback", methods=["POST"])
def feedback():
    payload = request.get_json(silent=True) or {}
    conversation_id = payload.get("conversation_id")

    if not conversation_id:
        return jsonify({"error": "conversation_id is required"}), 400

    entry = UserFeedback(
        conversation_id=conversation_id,
        rating=payload.get("rating"),
        helpful=payload.get("helpful"),
        emotion_accurate=payload.get("emotion_accurate"),
        comments=payload.get("comments"),
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify({"message": "Feedback saved"})


# =========================================================
# STARTUP
# =========================================================

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000, use_reloader=False)