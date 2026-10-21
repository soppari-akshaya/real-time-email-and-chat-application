from datetime import datetime
from models.database import db

class Email(db.Model):
    __tablename__ = 'emails'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_emails = db.Column(db.Text, nullable=False)  # comma separated
    subject = db.Column(db.String(255), default="(No Subject)")
    body = db.Column(db.Text, nullable=True)
    
    # Mailbox folder state
    folder = db.Column(db.String(20), default='inbox')  # inbox, sent, drafts, trash
    is_starred = db.Column(db.Boolean, default=False)
    is_important = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    labels = db.Column(db.String(120), default='General')  # e.g., 'Work', 'Personal', 'Urgent'
    
    in_reply_to_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    attachments = db.relationship('EmailAttachment', backref='email', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'sender_email': self.sender.email if self.sender else "system@omnisync.com",
            'sender_name': self.sender.username if self.sender else "System",
            'recipient_emails': self.recipient_emails,
            'subject': self.subject,
            'body': self.body,
            'folder': self.folder,
            'is_starred': self.is_starred,
            'is_important': self.is_important,
            'is_read': self.is_read,
            'labels': [l.strip() for l in self.labels.split(',') if l.strip()] if self.labels else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'date_str': self.created_at.strftime('%b %d, %I:%M %p') if self.created_at else '',
            'attachments': [a.to_dict() for a in self.attachments.all()]
        }


class EmailAttachment(db.Model):
    __tablename__ = 'email_attachments'

    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.Integer, db.ForeignKey('emails.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    file_type = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_type': self.file_type
        }
