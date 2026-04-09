import streamlit as st
import requests
import pandas as pd

# =========================================================
# CONFIG
# =========================================================

BASE_URL = "http://127.0.0.1:5000"
CHAT_URL = f"{BASE_URL}/chat"
HEALTH_URL = f"{BASE_URL}/health"
SUMMARY_URL = f"{BASE_URL}/analytics/summary"
HEATMAP_URL = f"{BASE_URL}/analytics/heatmap"
EXPORT_CSV_URL = f"{BASE_URL}/analytics/export-csv"

st.set_page_config(
    page_title="Conversational AI Dashboard",
    layout="wide"
)

# =========================================================
# SESSION STATE
# =========================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = "main_user_session"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "emotions" not in st.session_state:
    st.session_state.emotions = []

if "intents" not in st.session_state:
    st.session_state.intents = []

if "needs" not in st.session_state:
    st.session_state.needs = []

if "last_response_source" not in st.session_state:
    st.session_state.last_response_source = None

if "last_reasoning" not in st.session_state:
    st.session_state.last_reasoning = []

# =========================================================
# HELPERS
# =========================================================

def get_health():
    try:
        response = requests.get(HEALTH_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None
    return None


def send_chat(message, session_id):
    response = requests.post(
        CHAT_URL,
        json={
            "message": message,
            "session_id": session_id
        },
        timeout=180
    )
    return response


def get_summary(session_id):
    try:
        response = requests.get(f"{SUMMARY_URL}/{session_id}", timeout=20)
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None
    return None


def get_heatmap_url(session_id):
    try:
        response = requests.get(f"{HEATMAP_URL}/{session_id}", timeout=30)
        if response.status_code == 200:
            data = response.json()
            return f"{BASE_URL}{data['heatmap_url']}"
    except Exception:
        return None
    return None


def get_csv_download_link(session_id):
    return f"{EXPORT_CSV_URL}/{session_id}"


# =========================================================
# HEADER
# =========================================================

st.title("🧠 Intelligent Conversational AI Dashboard")
st.caption("Emotion Detection • Intent Classification • Need Reasoning • LLM Response Generation")

health = get_health()

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric("Session ID", st.session_state.session_id)

with col_b:
    if st.session_state.messages:
        st.metric("Total Interactions", len(st.session_state.messages) // 2)
    else:
        st.metric("Total Interactions", 0)

with col_c:
    if health:
        if health.get("llm_enabled"):
            st.success(f"LLM Enabled: {health.get('model', 'unknown')}")
        else:
            st.warning("LLM Disabled")
    else:
        st.error("Backend Offline")

st.divider()

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("⚙️ Controls")

new_session_id = st.sidebar.text_input("Session ID", value=st.session_state.session_id)
if new_session_id != st.session_state.session_id:
    st.session_state.session_id = new_session_id

if st.sidebar.button("Clear Current Chat"):
    st.session_state.messages = []
    st.session_state.emotions = []
    st.session_state.intents = []
    st.session_state.needs = []
    st.session_state.last_response_source = None
    st.session_state.last_reasoning = []
    st.rerun()

st.sidebar.markdown("---")

if st.session_state.last_response_source:
    st.sidebar.write("**Last Response Source:**", st.session_state.last_response_source)

if health:
    st.sidebar.write("**Backend Status:** Online")
    st.sidebar.write("**Model:**", health.get("model", "unknown"))
    st.sidebar.write("**LLM Enabled:**", health.get("llm_enabled", False))
else:
    st.sidebar.write("**Backend Status:** Offline")

# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Analytics", "📁 Session Tools"])

# =========================================================
# CHAT TAB
# =========================================================

with tab1:
    st.subheader("Chat Interface")

    # chat history
    for sender, msg in st.session_state.messages:
        if sender == "You":
            with st.chat_message("user"):
                st.write(msg)
        else:
            with st.chat_message("assistant"):
                st.write(msg)

    user_input = st.chat_input("Type your message...")

    if user_input:
        try:
            response = send_chat(user_input, st.session_state.session_id)

            if response.status_code != 200:
                st.error(f"Backend error: {response.status_code} - {response.text}")
            else:
                data = response.json()

                st.session_state.messages.append(("You", user_input))
                st.session_state.messages.append(("Bot", data.get("response", "")))

                st.session_state.emotions.append(data.get("emotion", "neutral"))
                st.session_state.intents.append(data.get("intent", "general"))
                st.session_state.needs.append(data.get("needs", "conversation"))

                st.session_state.last_response_source = data.get("response_source", "unknown")
                st.session_state.last_reasoning = data.get("reasoning_summary", [])

                with st.chat_message("assistant"):
                    st.write(data.get("response", ""))

                with st.expander("🧠 Reasoning Details", expanded=True):
                    st.write(f"**Emotion:** {data.get('emotion', 'neutral')}")
                    st.write(f"**Intent:** {data.get('intent', 'general')}")
                    st.write(f"**Need:** {data.get('needs', 'conversation')}")
                    st.write(f"**Response Source:** {data.get('response_source', 'unknown')}")

                    reasoning_summary = data.get("reasoning_summary", [])
                    if reasoning_summary:
                        st.write("**Reasoning Summary:**")
                        for item in reasoning_summary:
                            st.write(f"- {item}")

                    if data.get("response_source") == "fallback-rule-engine":
                        st.warning("Running without LLM response generation")
                    elif data.get("response_source") == "error-fallback":
                        st.error("Response generation failed and fallback was used")
                    else:
                        st.success(f"Using LLM: {data.get('response_source')}")

        except Exception as e:
            st.error(f"Error connecting to backend: {e}")

# =========================================================
# ANALYTICS TAB
# =========================================================

with tab2:
    st.subheader("Analytics Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.write("### Emotion Distribution")
        if st.session_state.emotions:
            df_emotion = pd.DataFrame(st.session_state.emotions, columns=["emotion"])
            emotion_counts = df_emotion["emotion"].value_counts()
            st.bar_chart(emotion_counts)
        else:
            st.info("No emotion data yet")

    with col2:
        st.write("### Intent Distribution")
        if st.session_state.intents:
            df_intent = pd.DataFrame(st.session_state.intents, columns=["intent"])
            intent_counts = df_intent["intent"].value_counts()
            st.bar_chart(intent_counts)
        else:
            st.info("No intent data yet")

    st.markdown("---")

    summary = get_summary(st.session_state.session_id)

    st.write("### Session Summary")
    if summary:
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Messages", summary.get("total_messages", 0))
        s2.metric("Dominant Emotion", summary.get("dominant_emotion", "N/A"))
        s3.metric("Avg Intensity", round(summary.get("avg_intensity", 0), 2))
        s4.metric("Avg Sentiment", round(summary.get("avg_sentiment", 0), 2))

        st.write("**Top Intents:**")
        st.json(summary.get("primary_intents", {}))

        timeline = summary.get("emotion_timeline", [])
        if timeline:
            timeline_df = pd.DataFrame(timeline)
            if "timestamp" in timeline_df.columns and "intensity" in timeline_df.columns:
                st.write("### Emotion Intensity Timeline")
                timeline_df["timestamp"] = pd.to_datetime(timeline_df["timestamp"])
                timeline_df = timeline_df.sort_values("timestamp")
                st.line_chart(timeline_df.set_index("timestamp")["intensity"])
    else:
        st.info("No backend session summary available yet")

# =========================================================
# SESSION TOOLS TAB
# =========================================================

with tab3:
    st.subheader("Session Tools")

    col1, col2 = st.columns(2)

    with col1:
        st.write("### Emotion Heatmap")
        if st.button("Generate Heatmap"):
            heatmap_url = get_heatmap_url(st.session_state.session_id)
            if heatmap_url:
                st.image(heatmap_url, caption="Emotion Transition Heatmap", use_container_width=True)
            else:
                st.warning("Need at least 2 saved messages to generate heatmap")

    with col2:
        st.write("### Export Session Data")
        csv_link = get_csv_download_link(st.session_state.session_id)
        st.markdown(
            f"[Download Session CSV]({csv_link})"
        )

    st.markdown("---")
    st.write("### Current Session Snapshot")
    st.write(f"**Session ID:** {st.session_state.session_id}")
    st.write(f"**Messages in UI memory:** {len(st.session_state.messages)//2}")

    if st.session_state.last_response_source:
        st.write(f"**Last Response Source:** {st.session_state.last_response_source}")