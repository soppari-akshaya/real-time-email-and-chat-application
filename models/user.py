from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar_url = db.Column(db.String(256), nullable=True)
    bio = db.Column(db.String(255), default="Hey there! I am using OmniSync.")
    role = db.Column(db.String(20), default='user')  # 'user' or 'admin'
    
    # Presence & Activity
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sent_messages = db.relationship('Message', backref='sender', lazy='dynamic', foreign_keys='Message.sender_id')
    memberships = db.relationship('ConversationMember', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sent_emails = db.relationship('Email', backref='sender', lazy='dynamic', foreign_keys='Email.sender_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar_url': self.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={self.username}",
            'bio': self.bio,
            'role': self.role,
            'is_online': self.is_online,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
