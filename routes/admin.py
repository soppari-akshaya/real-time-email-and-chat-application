from flask import Blueprint, render_template, session, redirect, url_for, flash
from models import db, User, Conversation, Message, Email
from routes.auth import login_required, get_current_user

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
def admin_dashboard():
    user = get_current_user()
    
    total_users = User.query.count()
    online_users = User.query.filter_by(is_online=True).count()
    total_conversations = Conversation.query.count()
    group_conversations = Conversation.query.filter_by(is_group=True).count()
    direct_conversations = Conversation.query.filter_by(is_group=False).count()
    total_messages = Message.query.count()
    total_emails = Email.query.count()

    all_users = User.query.order_by(User.created_at.desc()).all()
    recent_messages = Message.query.order_by(Message.created_at.desc()).limit(10).all()

    stats = {
        'total_users': total_users,
        'online_users': online_users,
        'total_conversations': total_conversations,
        'group_conversations': group_conversations,
        'direct_conversations': direct_conversations,
        'total_messages': total_messages,
        'total_emails': total_emails
    }

    return render_template('admin.html', current_user=user, stats=stats, users=all_users, recent_messages=recent_messages)
