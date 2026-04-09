import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from models import Conversation


class EmotionAnalytics:
    def __init__(self, exports_dir='exports'):
        self.exports_dir = exports_dir
        os.makedirs(self.exports_dir, exist_ok=True)

    def get_emotion_distribution(self, days=30):
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        conversations = Conversation.query.filter(Conversation.timestamp >= cutoff_date).all()
        df = pd.DataFrame([c.to_dict() for c in conversations])
        if df.empty:
            return {}
        return df['emotion'].value_counts().to_dict()

    def get_daily_emotion_trends(self, days=7):
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        conversations = Conversation.query.filter(Conversation.timestamp >= cutoff_date).all()
        df = pd.DataFrame([c.to_dict() for c in conversations])
        if df.empty:
            return {}
        df['date'] = pd.to_datetime(df['timestamp']).dt.date.astype(str)
        trends = df.groupby(['date', 'emotion']).size().unstack(fill_value=0)
        return trends.to_dict()

    def generate_emotion_heatmap(self, session_id=None):
        query = Conversation.query
        if session_id:
            query = query.filter_by(session_id=session_id)
        conversations = query.order_by(Conversation.timestamp).all()
        if len(conversations) < 2:
            return None

        emotions = [c.emotion_primary or 'neutral' for c in conversations]
        unique_emotions = sorted(set(emotions))
        transition_matrix = pd.DataFrame(0, index=unique_emotions, columns=unique_emotions)

        for i in range(len(emotions) - 1):
            transition_matrix.loc[emotions[i], emotions[i + 1]] += 1

        plt.figure(figsize=(10, 8))
        sns.heatmap(transition_matrix, annot=True, cmap='YlOrRd', fmt='g')
        plt.title('Emotion Transition Heatmap')
        plt.xlabel('Next Emotion')
        plt.ylabel('Current Emotion')
        plt.tight_layout()

        filename = f'emotion_heatmap_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        filepath = os.path.join(self.exports_dir, filename)
        plt.savefig(filepath)
        plt.close()
        return filename

    def get_session_summary(self, session_id):
        conversations = Conversation.query.filter_by(session_id=session_id).order_by(Conversation.timestamp).all()
        if not conversations:
            return None

        df = pd.DataFrame([c.to_dict() for c in conversations])
        summary = {
            'session_id': session_id,
            'total_messages': len(conversations),
            'start_time': conversations[0].timestamp.isoformat(),
            'end_time': conversations[-1].timestamp.isoformat(),
            'dominant_emotion': df['emotion'].mode()[0] if not df.empty else None,
            'avg_intensity': float(df['intensity'].fillna(0).mean()),
            'avg_sentiment': float(df['sentiment'].fillna(0).mean()),
            'emotion_changes': int(df['emotion'].nunique()),
            'primary_intents': df['intent'].value_counts().head(3).to_dict(),
            'response_time_avg': float(df['response_time'].fillna(0).mean()),
            'emotion_timeline': df[['timestamp', 'emotion', 'intensity']].to_dict('records')
        }
        return summary

    def export_session_csv(self, session_id):
        conversations = Conversation.query.filter_by(session_id=session_id).order_by(Conversation.timestamp).all()
        if not conversations:
            return None
        df = pd.DataFrame([c.to_dict() for c in conversations])
        filename = f'session_{session_id}.csv'
        filepath = os.path.join(self.exports_dir, filename)
        df.to_csv(filepath, index=False)
        return filename
