from datetime import datetime
from models.database import db

class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    is_group = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(120), nullable=True)  # Group name (or None for 1-to-1)
    description = db.Column(db.String(255), nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = db.relationship('ConversationMember', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='conversation', lazy='dynamic', cascade='all, delete-orphan', order_by='Message.created_at.asc()')

    def get_display_name(self, current_user_id):
        if self.is_group:
            return self.name or "Unnamed Group"
        # For 1-on-1, return the other member's username
        other_member = self.members.filter(ConversationMember.user_id != current_user_id).first()
        return other_member.user.username if (other_member and other_member.user) else "Chat"

    def get_display_avatar(self, current_user_id):
        if self.is_group:
            return self.avatar_url or f"https://api.dicebear.com/7.x/identicon/svg?seed={self.name or 'group'}"
        other_member = self.members.filter(ConversationMember.user_id != current_user_id).first()
        if other_member and other_member.user:
            return other_member.user.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={other_member.user.username}"
        return "https://api.dicebear.com/7.x/bottts/svg?seed=chat"

    def get_other_user(self, current_user_id):
        if self.is_group:
            return None
        other_member = self.members.filter(ConversationMember.user_id != current_user_id).first()
        return other_member.user if other_member else None

    def to_dict(self, current_user_id=None):
        last_msg = self.messages.order_by(Message.created_at.desc()).first()
        
        # Calculate unread count for current user
        unread_count = 0
        if current_user_id:
            membership = self.members.filter_by(user_id=current_user_id).first()
            if membership:
                last_read_id = membership.last_read_message_id or 0
                unread_count = self.messages.filter(Message.id > last_read_id, Message.sender_id != current_user_id).count()

        other_user = self.get_other_user(current_user_id) if current_user_id else None

        return {
            'id': self.id,
            'is_group': self.is_group,
            'name': self.get_display_name(current_user_id) if current_user_id else self.name,
            'raw_name': self.name,
            'description': self.description,
            'avatar_url': self.get_display_avatar(current_user_id) if current_user_id else self.avatar_url,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'unread_count': unread_count,
            'last_message': last_msg.to_dict() if last_msg else None,
            'other_user': other_user.to_dict() if other_user else None,
            'member_count': self.members.count()
        }


class ConversationMember(db.Model):
    __tablename__ = 'conversation_members'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_read_message_id = db.Column(db.Integer, nullable=True, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'avatar_url': self.user.to_dict()['avatar_url'] if self.user else None,
            'is_online': self.user.is_online if self.user else False,
            'last_seen': self.user.last_seen.isoformat() if (self.user and self.user.last_seen) else None,
            'is_admin': self.is_admin,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'last_read_message_id': self.last_read_message_id
        }


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    text = db.Column(db.Text, nullable=True)
    message_type = db.Column(db.String(20), default='text')  # text, image, file
    file_path = db.Column(db.String(255), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # in bytes
    
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Delivery & Read Status records
    statuses = db.relationship('MessageStatus', backref='message', lazy='dynamic', cascade='all, delete-orphan')

    def get_status_summary(self, current_user_id=None):
        """Calculates sent / delivered / read for this message"""
        if self.is_deleted:
            return 'deleted'
        
        # Read receipts from conversation members
        conv = self.conversation
        if not conv:
            return 'sent'
        
        other_members = conv.members.filter(ConversationMember.user_id != self.sender_id).all()
        if not other_members:
            return 'sent'
        
        # Check if any or all other members have read this message
        read_by_all = all((m.last_read_message_id or 0) >= self.id for m in other_members)
        if read_by_all:
            return 'read'
        
        read_by_any = any((m.last_read_message_id or 0) >= self.id for m in other_members)
        if read_by_any:
            return 'read'
        
        # Delivered if recipient is currently online
        any_online = any(m.user and m.user.is_online for m in other_members)
        if any_online:
            return 'delivered'
        
        return 'sent'

    def to_dict(self, current_user_id=None):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.username if self.sender else "Unknown",
            'sender_avatar': self.sender.to_dict()['avatar_url'] if self.sender else None,
            'text': "This message was deleted" if self.is_deleted else self.text,
            'message_type': self.message_type if not self.is_deleted else 'text',
            'file_path': self.file_path if not self.is_deleted else None,
            'file_name': self.file_name if not self.is_deleted else None,
            'file_size': self.file_size if not self.is_deleted else None,
            'is_edited': self.is_edited and not self.is_deleted,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'timestamp_str': self.created_at.strftime('%I:%M %p') if self.created_at else '',
            'date_str': self.created_at.strftime('%Y-%m-%d') if self.created_at else '',
            'status': self.get_status_summary(current_user_id)
        }


class MessageStatus(db.Model):
    __tablename__ = 'message_statuses'

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='sent')  # sent, delivered, read
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
