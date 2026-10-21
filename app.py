import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from db import users, conversations, messages, emails, to_id

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple-chat-secret-key'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

socketio = SocketIO(app, cors_allowed_origins="*")

# Helper: Get current user (No login required, defaults to Alice / id: 1)
def get_current_user():
    user_id = session.get('user_id', 1)
    user = users.find_one({'id': user_id})
    if not user:
        user = users.find_one()
        if user:
            session['user_id'] = user['id']
    return user

def format_msg(msg):
    """Helper to format MongoDB message doc for JSON"""
    created_at = msg.get('created_at', datetime.utcnow())
    return {
        'id': str(msg['_id']),
        'conversation_id': str(msg['conversation_id']),
        'sender_id': msg['sender_id'],
        'sender_name': msg.get('sender_name', 'Unknown'),
        'text': 'This message was deleted' if msg.get('is_deleted') else msg.get('text', ''),
        'file_url': None if msg.get('is_deleted') else msg.get('file_url'),
        'file_name': None if msg.get('is_deleted') else msg.get('file_name'),
        'is_edited': msg.get('is_edited', False) and not msg.get('is_deleted'),
        'is_deleted': msg.get('is_deleted', False),
        'time': created_at.strftime('%I:%M %p'),
        'date': created_at.strftime('%Y-%m-%d')
    }

@app.context_processor
def inject_globals():
    cur = get_current_user()
    all_u = list(users.find())
    return {
        'current_user': cur,
        'all_users': all_u
    }

# Route to easily switch active user from dropdown
@app.route('/switch-user/<int:user_id>')
def switch_user(user_id):
    session['user_id'] = user_id
    referrer = request.referrer or url_for('chat_page')
    return redirect(referrer)

# ==========================================
# MEMBER 2: CHAT MODULE ROUTES (MONGODB)
# ==========================================

@app.route('/')
@app.route('/chat')
def chat_page():
    user = get_current_user()
    other_users = list(users.find({'id': {'$ne': user['id']}})) if user else []
    return render_template('chat.html', current_user=user, other_users=other_users)

@app.route('/api/conversations')
def get_conversations():
    user = get_current_user()
    if not user:
        return jsonify([])

    # Find conversations where current user is a member
    user_convs = list(conversations.find({'members.user_id': user['id']}).sort('created_at', -1))

    result = []
    for c in user_convs:
        conv_id_str = str(c['_id'])

        if c.get('is_group'):
            display_name = c.get('name', 'Group')
            is_online = False
        else:
            # Find the other member in 1-on-1 chat
            other_mem = next((m for m in c.get('members', []) if m['user_id'] != user['id']), None)
            if other_mem:
                other_user = users.find_one({'id': other_mem['user_id']})
                display_name = other_user['name'] if other_user else 'Direct Chat'
                is_online = other_user.get('is_online', False) if other_user else False
            else:
                display_name = 'Direct Chat'
                is_online = False

        # Get last message
        last_msg = messages.find_one({'conversation_id': conv_id_str}, sort=[('created_at', -1)])

        # Count unread messages
        user_mem = next((m for m in c.get('members', []) if m['user_id'] == user['id']), None)
        last_read_time = user_mem.get('last_read_time', datetime.min) if user_mem else datetime.min
        unread = messages.count_documents({
            'conversation_id': conv_id_str,
            'sender_id': {'$ne': user['id']},
            'created_at': {'$gt': last_read_time}
        })

        result.append({
            'id': conv_id_str,
            'is_group': c.get('is_group', False),
            'name': display_name,
            'is_online': is_online,
            'last_message': last_msg.get('text', '') if last_msg else '',
            'last_time': last_msg['created_at'].strftime('%I:%M %p') if last_msg else '',
            'unread_count': unread
        })

    return jsonify(result)

# Start or fetch 1-to-1 conversation
@app.route('/api/conversations/direct/<int:target_user_id>', methods=['POST'])
def start_direct_chat(target_user_id):
    user = get_current_user()
    if user['id'] == target_user_id:
        return jsonify({'error': 'Cannot chat with yourself'}), 400

    # Look for existing 1-on-1 chat with both user IDs
    existing = conversations.find_one({
        'is_group': False,
        '$and': [
            {'members.user_id': user['id']},
            {'members.user_id': target_user_id}
        ]
    })

    if existing:
        return jsonify({'id': str(existing['_id'])})

    now = datetime.utcnow()
    new_conv = {
        'is_group': False,
        'name': None,
        'members': [
            {'user_id': user['id'], 'is_admin': True, 'last_read_time': now},
            {'user_id': target_user_id, 'is_admin': False, 'last_read_time': now}
        ],
        'created_at': now
    }
    inserted = conversations.insert_one(new_conv)
    return jsonify({'id': str(inserted.inserted_id)})

# Create Group Chat
@app.route('/api/conversations/group', methods=['POST'])
def create_group():
    user = get_current_user()
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    member_ids = data.get('member_ids', [])

    if not name:
        return jsonify({'error': 'Group name required'}), 400

    now = datetime.utcnow()
    members_list = [{'user_id': user['id'], 'is_admin': True, 'last_read_time': now}]
    for uid in member_ids:
        if uid != user['id']:
            members_list.append({'user_id': uid, 'is_admin': False, 'last_read_time': now})

    new_group = {
        'is_group': True,
        'name': name,
        'members': members_list,
        'created_at': now
    }
    inserted = conversations.insert_one(new_group)
    conv_id_str = str(inserted.inserted_id)

    # Initial welcome message
    messages.insert_one({
        'conversation_id': conv_id_str,
        'sender_id': user['id'],
        'sender_name': user['name'],
        'text': f"Group '{name}' was created.",
        'file_url': None,
        'file_name': None,
        'is_edited': False,
        'is_deleted': False,
        'created_at': now
    })

    return jsonify({'id': conv_id_str, 'name': name})

# Get messages for a conversation
@app.route('/api/conversations/<conv_id>/messages')
def get_messages(conv_id):
    user = get_current_user()
    search = request.args.get('q', '').strip()

    filter_query = {'conversation_id': conv_id}
    if search:
        filter_query['text'] = {'$regex': search, '$options': 'i'}

    msg_docs = list(messages.find(filter_query).sort('created_at', 1))

    # Mark as read
    conversations.update_one(
        {'_id': to_id(conv_id), 'members.user_id': user['id']},
        {'$set': {'members.$.last_read_time': datetime.utcnow()}}
    )

    conv_doc = conversations.find_one({'_id': to_id(conv_id)})
    members_data = []
    is_admin = False

    if conv_doc:
        for m in conv_doc.get('members', []):
            u = users.find_one({'id': m['user_id']})
            if u:
                members_data.append({
                    'user_id': u['id'],
                    'name': u['name'],
                    'is_admin': m.get('is_admin', False),
                    'is_online': u.get('is_online', False)
                })
            if m['user_id'] == user['id'] and m.get('is_admin'):
                is_admin = True

    return jsonify({
        'messages': [format_msg(m) for m in msg_docs],
        'members': members_data,
        'is_group': conv_doc.get('is_group', False) if conv_doc else False,
        'is_admin': is_admin
    })

# Upload image or document in chat
@app.route('/api/conversations/<conv_id>/upload', methods=['POST'])
def upload_chat_file(conv_id):
    user = get_current_user()
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    rel_url = url_for('static', filename=f'uploads/{filename}')
    now = datetime.utcnow()

    msg_doc = {
        'conversation_id': conv_id,
        'sender_id': user['id'],
        'sender_name': user['name'],
        'text': file.filename,
        'file_url': rel_url,
        'file_name': file.filename,
        'is_edited': False,
        'is_deleted': False,
        'created_at': now
    }
    inserted = messages.insert_one(msg_doc)
    msg_doc['_id'] = inserted.inserted_id

    formatted = format_msg(msg_doc)
    socketio.emit('new_message', formatted, to=f"room_{conv_id}")

    return jsonify(formatted)

# Add member to group
@app.route('/api/conversations/<conv_id>/add-member', methods=['POST'])
def add_group_member(conv_id):
    data = request.get_json() or {}
    user_id = data.get('user_id')
    user = users.find_one({'id': user_id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    conv = conversations.find_one({'_id': to_id(conv_id)})
    if not conv:
        return jsonify({'error': 'Conversation not found'}), 404

    # Check if already a member
    if any(m['user_id'] == user_id for m in conv.get('members', [])):
        return jsonify({'error': 'Already a member'}), 400

    conversations.update_one(
        {'_id': to_id(conv_id)},
        {'$push': {'members': {'user_id': user_id, 'is_admin': False, 'last_read_time': datetime.utcnow()}}}
    )
    return jsonify({'success': True})

# Remove member from group
@app.route('/api/conversations/<conv_id>/remove-member/<int:user_id>', methods=['POST'])
def remove_group_member(conv_id, user_id):
    conversations.update_one(
        {'_id': to_id(conv_id)},
        {'$pull': {'members': {'user_id': user_id}}}
    )
    return jsonify({'success': True})

# ==========================================
# MEMBER 1: EMAIL MODULE (SHARED MONGODB)
# ==========================================

@app.route('/email')
def email_page():
    user = get_current_user()
    folder = request.args.get('folder', 'inbox')
    return render_template('email.html', current_user=user, current_folder=folder)

@app.route('/api/emails')
def get_emails():
    user = get_current_user()
    folder = request.args.get('folder', 'inbox')
    search = request.args.get('q', '').strip()

    if folder == 'sent':
        query = {'sender_id': user['id'], 'folder': 'sent'}
    elif folder == 'trash':
        query = {'folder': 'trash'}
    else: # inbox
        query = {'recipient_email': {'$regex': user['email'], '$options': 'i'}, 'folder': 'inbox'}

    if search:
        query['$or'] = [
            {'subject': {'$regex': search, '$options': 'i'}},
            {'body': {'$regex': search, '$options': 'i'}}
        ]

    email_docs = list(emails.find(query).sort('created_at', -1))
    res = []
    for e in email_docs:
        res.append({
            'id': str(e['_id']),
            'sender_name': e.get('sender_name', 'System'),
            'sender_email': e.get('sender_email', ''),
            'recipient_email': e.get('recipient_email', ''),
            'subject': e.get('subject', '(No Subject)'),
            'body': e.get('body', ''),
            'date': e.get('created_at', datetime.utcnow()).strftime('%b %d, %I:%M %p'),
            'is_starred': e.get('is_starred', False),
            'is_important': e.get('is_important', False)
        })
    return jsonify(res)

@app.route('/api/emails/send', methods=['POST'])
def send_email():
    user = get_current_user()
    recipient = request.form.get('recipient', '').strip()
    subject = request.form.get('subject', '').strip() or '(No Subject)'
    body = request.form.get('body', '').strip()

    now = datetime.utcnow()
    # Save sent email
    emails.insert_one({
        'sender_id': user['id'],
        'sender_name': user['name'],
        'sender_email': user['email'],
        'recipient_email': recipient,
        'subject': subject,
        'body': body,
        'folder': 'sent',
        'is_starred': False,
        'is_important': False,
        'created_at': now
    })
    # Save inbox copy for recipient
    emails.insert_one({
        'sender_id': user['id'],
        'sender_name': user['name'],
        'sender_email': user['email'],
        'recipient_email': recipient,
        'subject': subject,
        'body': body,
        'folder': 'inbox',
        'is_starred': False,
        'is_important': False,
        'created_at': now
    })
    return jsonify({'success': True})

# ==========================================
# SOCKET.IO REAL-TIME HANDLERS (MEMBER 2)
# ==========================================

@socketio.on('connect')
def on_connect():
    user = get_current_user()
    if user:
        users.update_one({'id': user['id']}, {'$set': {'is_online': True}})
        emit('status_change', {'user_id': user['id'], 'is_online': True}, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    user = get_current_user()
    if user:
        users.update_one({'id': user['id']}, {'$set': {'is_online': False}})
        emit('status_change', {'user_id': user['id'], 'is_online': False}, broadcast=True)

@socketio.on('join_room')
def on_join_room(data):
    room = f"room_{data.get('conversation_id')}"
    join_room(room)

@socketio.on('leave_room')
def on_leave_room(data):
    room = f"room_{data.get('conversation_id')}"
    leave_room(room)

@socketio.on('send_message')
def on_send_message(data):
    user = get_current_user()
    conv_id = data.get('conversation_id')
    text = data.get('text', '').strip()

    if not conv_id or not text:
        return

    now = datetime.utcnow()
    msg_doc = {
        'conversation_id': conv_id,
        'sender_id': user['id'],
        'sender_name': user['name'],
        'text': text,
        'file_url': None,
        'file_name': None,
        'is_edited': False,
        'is_deleted': False,
        'created_at': now
    }
    inserted = messages.insert_one(msg_doc)
    msg_doc['_id'] = inserted.inserted_id

    formatted = format_msg(msg_doc)
    # Broadcast to active conversation room
    emit('new_message', formatted, to=f"room_{conv_id}")

    # Emit notification to all other clients
    emit('message_notification', {
        'conversation_id': conv_id,
        'sender_id': user['id'],
        'sender_name': user['name'],
        'text': text
    }, broadcast=True)

@socketio.on('typing')
def on_typing(data):
    user = get_current_user()
    conv_id = data.get('conversation_id')
    emit('user_typing', {
        'conversation_id': conv_id,
        'username': user['name'],
        'user_id': user['id']
    }, to=f"room_{conv_id}", include_self=False)

@socketio.on('stop_typing')
def on_stop_typing(data):
    conv_id = data.get('conversation_id')
    emit('user_stop_typing', {'conversation_id': conv_id}, to=f"room_{conv_id}", include_self=False)

@socketio.on('mark_read')
def on_mark_read(data):
    user = get_current_user()
    conv_id = data.get('conversation_id')
    if conv_id and user:
        conversations.update_one(
            {'_id': to_id(conv_id), 'members.user_id': user['id']},
            {'$set': {'members.$.last_read_time': datetime.utcnow()}}
        )
        emit('read_receipt', {'conversation_id': conv_id}, to=f"room_{conv_id}")

@socketio.on('edit_message')
def on_edit_message(data):
    msg_id = data.get('message_id')
    new_text = data.get('text', '').strip()
    if msg_id and new_text:
        messages.update_one(
            {'_id': to_id(msg_id)},
            {'$set': {'text': new_text, 'is_edited': True}}
        )
        msg = messages.find_one({'_id': to_id(msg_id)})
        if msg:
            emit('message_edited', {
                'id': str(msg['_id']),
                'conversation_id': msg['conversation_id'],
                'text': new_text
            }, to=f"room_{msg['conversation_id']}")

@socketio.on('delete_message')
def on_delete_message(data):
    msg_id = data.get('message_id')
    if msg_id:
        messages.update_one(
            {'_id': to_id(msg_id)},
            {'$set': {'is_deleted': True, 'text': 'This message was deleted'}}
        )
        msg = messages.find_one({'_id': to_id(msg_id)})
        if msg:
            emit('message_deleted', {
                'id': str(msg['_id']),
                'conversation_id': msg['conversation_id']
            }, to=f"room_{msg['conversation_id']}")

if __name__ == '__main__':
    print("🚀 MongoDB Real-Time Chat & Email Server running at http://127.0.0.1:5000")
    socketio.run(app, debug=True, host='127.0.0.1', port=5000)
