from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# User Table (shared between Email and Chat)
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    is_online = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'is_online': self.is_online
        }

# Conversation Table (1-to-1 and Group chats)
class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    is_group = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100), nullable=True)  # Name for groups
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('ConversationMember', backref='conversation', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='conversation', cascade='all, delete-orphan')

# Members of a conversation
class ConversationMember(db.Model):
    __tablename__ = 'conversation_members'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    last_read_id = db.Column(db.Integer, default=0)

    user = db.relationship('User')

# Chat Messages
class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    text = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(255), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.name if self.sender else 'Unknown',
            'text': 'This message was deleted' if self.is_deleted else self.text,
            'file_url': None if self.is_deleted else self.file_url,
            'file_name': None if self.is_deleted else self.file_name,
            'is_edited': self.is_edited and not self.is_deleted,
            'is_deleted': self.is_deleted,
            'time': self.created_at.strftime('%I:%M %p'),
            'date': self.created_at.strftime('%Y-%m-%d')
        }

# Email Table (Member 1 module)
class Email(db.Model):
    __tablename__ = 'emails'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), default='(No Subject)')
    body = db.Column(db.Text, nullable=True)
    folder = db.Column(db.String(20), default='inbox')  # inbox, sent, drafts, trash
    is_starred = db.Column(db.Boolean, default=False)
    is_important = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User')
    attachments = db.relationship('EmailAttachment', backref='email', cascade='all, delete-orphan')

# Email Attachments (Member 1 module)
class EmailAttachment(db.Model):
    __tablename__ = 'email_attachments'
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.Integer, db.ForeignKey('emails.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
