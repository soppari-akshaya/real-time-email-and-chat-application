import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app, url_for
from werkzeug.utils import secure_filename
from models import (
    get_all_users, get_user_conversations, get_or_create_direct_conversation,
    create_group_conversation, get_conversation_details, get_conversation_messages,
    create_message, mark_conversation_read, add_group_member, remove_group_member,
    get_user_by_email, clear_conversation_messages
)
from utils import get_current_user, login_required
from extensions import socketio

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/')
def index():
    user = get_current_user()
    other_users = get_all_users(exclude_user_id=user['id'] if user else None)
    return render_template('chat.html', current_user=user, other_users=other_users)

@chat_bp.route('/chat')
@login_required
def chat_page():
    user = get_current_user()
    other_users = get_all_users(exclude_user_id=user['id'])
    return render_template('chat.html', current_user=user, other_users=other_users)

@chat_bp.route('/api/conversations')
@login_required
def list_conversations():
    user = get_current_user()
    conversations = get_user_conversations(user['id'])
    return jsonify(conversations)

@chat_bp.route('/api/conversations/direct/<int:target_user_id>', methods=['POST'])
@login_required
def direct_chat(target_user_id):
    user = get_current_user()
    if user['id'] == target_user_id:
        return jsonify({'error': 'Cannot chat with yourself'}), 400

    conv_data = get_or_create_direct_conversation(user['id'], target_user_id)
    if not conv_data:
        return jsonify({'error': 'Target user not found'}), 404
    return jsonify(conv_data)

@chat_bp.route('/api/conversations/direct-by-email', methods=['POST'])
@login_required
def direct_chat_by_email():
    user = get_current_user()
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email address is required'}), 400

    if email == user['email'].lower():
        return jsonify({'error': 'Cannot start a chat with your own email'}), 400

    target_user = get_user_by_email(email)
    if not target_user:
        return jsonify({'error': f'No registered user found with email "{email}"'}), 404

    conv_data = get_or_create_direct_conversation(user['id'], target_user['id'])
    return jsonify(conv_data)

@chat_bp.route('/api/conversations/group', methods=['POST'])
@login_required
def create_group():
    user = get_current_user()
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    member_ids = data.get('member_ids', [])

    if not name:
        return jsonify({'error': 'Group name required'}), 400

    conv_data = create_group_conversation(user['id'], name, member_ids)
    return jsonify(conv_data)

@chat_bp.route('/api/conversations/<int:conv_id>/messages')
@login_required
def conversation_messages(conv_id):
    user = get_current_user()
    search = request.args.get('q', '').strip()

    messages = get_conversation_messages(conv_id, search_query=search)
    details = get_conversation_details(conv_id, user['id'])

    mark_conversation_read(conv_id, user['id'])

    if not details:
        return jsonify({'messages': [], 'members': [], 'is_group': False, 'is_admin': False})

    return jsonify({
        'messages': messages,
        'members': details['members'],
        'is_group': details['is_group'],
        'is_admin': details['is_admin'],
        'other_email': details['other_email'],
        'other_name': details['other_name']
    })

@chat_bp.route('/api/conversations/<int:conv_id>/upload', methods=['POST'])
@login_required
def upload_file(conv_id):
    user = get_current_user()
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    filename = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    caption = request.form.get('text', '').strip()
    rel_url = url_for('static', filename=f'uploads/{filename}')
    msg_data = create_message(conv_id, user['id'], user['name'], caption, file_url=rel_url, file_name=file.filename)

    socketio.emit('new_message', msg_data, to=f"room_{conv_id}")
    socketio.emit('message_notification', {
        'message_id': str(msg_data['id']),
        'conversation_id': str(conv_id),
        'sender_id': user['id'],
        'sender_name': user['name'],
        'text': caption or (f"Sent {file.filename}" if file.filename else "Sent an attachment")
    }, broadcast=True)
    return jsonify(msg_data)

@chat_bp.route('/api/conversations/<int:conv_id>/add-member', methods=['POST'])
@login_required
def add_member(conv_id):
    data = request.get_json() or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400

    add_group_member(conv_id, int(user_id))
    return jsonify({'success': True})

@chat_bp.route('/api/conversations/<int:conv_id>/remove-member/<int:user_id>', methods=['POST'])
@login_required
def remove_member(conv_id, user_id):
    remove_group_member(conv_id, user_id)
    return jsonify({'success': True})

@chat_bp.route('/api/conversations/<int:conv_id>/clear-history', methods=['POST'])
@login_required
def clear_history(conv_id):
    clear_conversation_messages(conv_id)
    socketio.emit('chat_history_cleared', {'conversation_id': conv_id}, to=f"room_{conv_id}")
    return jsonify({'success': True})
