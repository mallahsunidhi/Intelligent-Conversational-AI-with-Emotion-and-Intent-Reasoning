# 🧠 Intelligent Conversational AI with Emotion & Intent Reasoning

Most chatbots respond the same way to every user.
This system doesn’t.

It understands:

* **User Emotion** (anxiety, love, frustration, etc.)
* **User Intent** (advice, support, information)
* **Underlying Need** (guidance, reassurance, clarity)

Then it generates **context-aware, human-like responses** using LLMs.

---

## 🔍 Project Overview

This project is an advanced conversational AI system that combines:

* Emotion Detection
* Intent Classification
* Context Memory
* Rule-based + LLM hybrid reasoning

Unlike traditional chatbots, this system adapts its response based on how the user feels and what they need.

---

## ⚙️ Tech Stack

* **Backend:** Flask
* **Frontend:** Streamlit
* **LLM:** Llama 3.2 (via Ollama)
* **Database:** SQLite
* **Analytics:** Pandas, Matplotlib

---

## 🚀 Key Features

* 💬 Emotion-aware conversations
* 🎯 Intent-based response generation
* 🧠 Context memory using session tracking
* 📊 Real-time analytics dashboard
* 📈 Emotion heatmaps & session insights
* 🔁 Hybrid system (Rule-based + LLM)
* 🛠️ Fallback responses if LLM is unavailable

---

## 🏗️ Project Structure

```
emotionchat/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── analytics.py
│
├── frontend/
│   ├── app.py
│
├── requirements.txt
├── README.md
├── .gitignore
```

---

## ▶️ How to Run the Project

### 1. Clone the repository

```bash
git clone https://github.com/mallahsunidhi/Intelligent-Conversational-AI-with-Emotion-and-Intent-Reasoning.git
cd Intelligent-Conversational-AI-with-Emotion-and-Intent-Reasoning
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the backend

```bash
cd backend
python main.py
```

Open in browser:

```
http://127.0.0.1:5000
```

---

## 🤖 Optional: Enable LLM (Ollama)

To get real AI-generated responses:

```bash
ollama serve
ollama pull llama3.2
```

If Ollama is not running, the system will still work using fallback responses.

---

## 📊 Analytics & Insights

The system tracks:

* Emotion distribution across conversations
* User interaction patterns
* Session-based insights

Visualizations include:

* Emotion heatmaps
* Real-time interaction graphs

---

## 💡 Why This Project Matters

Most chatbots ignore user emotions.
This system attempts to bridge that gap by making AI more:

* Human-like
* Context-aware
* Emotion-sensitive

It’s a step toward emotionally intelligent AI systems.

---

## 🔮 Future Improvements

* Advanced emotion detection using ML models
* Voice-based interaction
* Multi-language support
* Deployment on cloud (AWS / Azure)
* Integration with real-time chat platforms

---

## 📌 Author

**Sunidhi Mallah**
Aspiring Data Analyst & AI Developer
