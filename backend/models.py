from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()


class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    emotion_primary = db.Column(db.String(50))
    emotion_intensity = db.Column(db.Float)
    sentiment_score = db.Column(db.Float)
    intent = db.Column(db.String(50))
    needs = db.Column(db.String(50))
    response_source = db.Column(db.String(50))
    response_time_ms = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
     return {
        'id': self.id,
        'session_id': self.session_id,
        'user_message': self.user_message,
        'bot_response': (self.bot_response[:100] + '...') if len(self.bot_response) > 100 else self.bot_response,
        'emotion': self.emotion_primary,
        'intensity': self.emotion_intensity,
        'sentiment': self.sentiment_score,
        'intent': self.intent,
        'needs': self.needs,
        'response_source': self.response_source,
        'response_time': self.response_time_ms,
        'timestamp': self.timestamp.isoformat()
    }


class UserFeedback(db.Model):
    __tablename__ = 'user_feedback'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'))
    rating = db.Column(db.Integer)
    helpful = db.Column(db.Boolean)
    emotion_accurate = db.Column(db.Boolean)
    comments = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
