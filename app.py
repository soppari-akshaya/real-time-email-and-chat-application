import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from models import db, User, Conversation, ConversationMember, Message, Email, EmailAttachment

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple-chat-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_email.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Helper: Get currently selected user (no login required)
def get_current_user():
    user_id = session.get('user_id', 1) # Default to Alice (User 1)
    user = User.query.get(user_id)
    if not user:
        user = User.query.first()
        if user:
            session['user_id'] = user.id
    return user

@app.context_processor
def inject_globals():
    return {
        'current_user': get_current_user(),
        'all_users': User.query.all()
    }

# Route to easily switch current user from navbar (No passwords/login needed)
@app.route('/switch-user/<int:user_id>')
def switch_user(user_id):
    session['user_id'] = user_id
    referrer = request.referrer or url_for('chat_page')
    return redirect(referrer)

# ==========================================
# MEMBER 2: CHAT MODULE ROUTES
# ==========================================

@app.route('/')
@app.route('/chat')
def chat_page():
    user = get_current_user()
    other_users = User.query.filter(User.id != user.id).all() if user else []
    return render_template('chat.html', current_user=user, other_users=other_users)

# Get all conversations for current user
@app.route('/api/conversations')
def get_conversations():
    user = get_current_user()
    if not user:
        return jsonify([])

    memberships = ConversationMember.query.filter_by(user_id=user.id).all()
    conv_ids = [m.conversation_id for m in memberships]
    conversations = Conversation.query.filter(Conversation.id.in_(conv_ids)).all()

    result = []
    for c in conversations:
        # Determine chat name and avatar
        if c.is_group:
            display_name = c.name
            is_online = False
        else:
            other = ConversationMember.query.filter(
                ConversationMember.conversation_id == c.id,
                ConversationMember.user_id != user.id
            ).first()
            display_name = other.user.name if other and other.user else "Direct Chat"
            is_online = other.user.is_online if other and other.user else False

        last_msg = Message.query.filter_by(conversation_id=c.id).order_by(Message.id.desc()).first()
        
        # Calculate unread count
        user_mem = ConversationMember.query.filter_by(conversation_id=c.id, user_id=user.id).first()
        last_read = user_mem.last_read_id if user_mem else 0
        unread = Message.query.filter(
            Message.conversation_id == c.id,
            Message.id > last_read,
            Message.sender_id != user.id
        ).count()

        result.append({
            'id': c.id,
            'is_group': c.is_group,
            'name': display_name,
            'is_online': is_online,
            'last_message': last_msg.text if last_msg else '',
            'last_time': last_msg.created_at.strftime('%I:%M %p') if last_msg else '',
            'unread_count': unread
        })

    return jsonify(result)

# Start or open a 1-to-1 chat
@app.route('/api/conversations/direct/<int:target_user_id>', methods=['POST'])
def start_direct_chat(target_user_id):
    user = get_current_user()
    if user.id == target_user_id:
        return jsonify({'error': 'Cannot chat with yourself'}), 400

    # Check if 1-on-1 chat already exists
    convs = Conversation.query.filter_by(is_group=False).all()
    for c in convs:
        uids = {m.user_id for m in c.members}
        if uids == {user.id, target_user_id}:
            return jsonify({'id': c.id})

    # Create new conversation
    new_conv = Conversation(is_group=False)
    db.session.add(new_conv)
    db.session.flush()

    m1 = ConversationMember(conversation_id=new_conv.id, user_id=user.id, is_admin=True)
    m2 = ConversationMember(conversation_id=new_conv.id, user_id=target_user_id, is_admin=False)
    db.session.add_all([m1, m2])
    db.session.commit()

    return jsonify({'id': new_conv.id})

# Create a group chat
@app.route('/api/conversations/group', methods=['POST'])
def create_group():
    user = get_current_user()
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    member_ids = data.get('member_ids', [])

    if not name:
        return jsonify({'error': 'Group name required'}), 400

    new_group = Conversation(is_group=True, name=name)
    db.session.add(new_group)
    db.session.flush()

    # Creator is admin
    db.session.add(ConversationMember(conversation_id=new_group.id, user_id=user.id, is_admin=True))

    # Add other members
    for uid in member_ids:
        if uid != user.id:
            db.session.add(ConversationMember(conversation_id=new_group.id, user_id=uid, is_admin=False))

    # Add welcome message
    msg = Message(conversation_id=new_group.id, sender_id=user.id, text=f"Group '{name}' was created.")
    db.session.add(msg)
    db.session.commit()

    return jsonify({'id': new_group.id, 'name': new_group.name})

# Get messages for a conversation (with search support)
@app.route('/api/conversations/<int:conv_id>/messages')
def get_messages(conv_id):
    user = get_current_user()
    search = request.args.get('q', '').strip()

    query = Message.query.filter_by(conversation_id=conv_id)
    if search:
        query = query.filter(Message.text.ilike(f'%{search}%'))

    messages = query.order_by(Message.created_at.asc()).all()

    # Mark as read
    mem = ConversationMember.query.filter_by(conversation_id=conv_id, user_id=user.id).first()
    if mem and messages:
        mem.last_read_id = messages[-1].id
        db.session.commit()

    # Get conversation details
    conv = Conversation.query.get(conv_id)
    members_list = []
    if conv:
        for m in conv.members:
            members_list.append({
                'user_id': m.user.id,
                'name': m.user.name,
                'is_admin': m.is_admin,
                'is_online': m.user.is_online
            })

    return jsonify({
        'messages': [m.to_dict() for m in messages],
        'members': members_list,
        'is_group': conv.is_group if conv else False,
        'is_admin': mem.is_admin if mem else False
    })

# Upload file / image in chat
@app.route('/api/conversations/<int:conv_id>/upload', methods=['POST'])
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

    msg = Message(
        conversation_id=conv_id,
        sender_id=user.id,
        text=file.filename,
        file_url=rel_url,
        file_name=file.filename
    )
    db.session.add(msg)
    db.session.commit()

    msg_data = msg.to_dict()
    socketio.emit('new_message', msg_data, to=f"room_{conv_id}")

    return jsonify(msg_data)

# Add member to group
@app.route('/api/conversations/<int:conv_id>/add-member', methods=['POST'])
def add_group_member(conv_id):
    data = request.get_json() or {}
    user_id = data.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    existing = ConversationMember.query.filter_by(conversation_id=conv_id, user_id=user_id).first()
    if existing:
        return jsonify({'error': 'Already a member'}), 400

    new_mem = ConversationMember(conversation_id=conv_id, user_id=user_id, is_admin=False)
    db.session.add(new_mem)
    db.session.commit()

    return jsonify({'success': True})

# Remove member from group
@app.route('/api/conversations/<int:conv_id>/remove-member/<int:user_id>', methods=['POST'])
def remove_group_member(conv_id, user_id):
    mem = ConversationMember.query.filter_by(conversation_id=conv_id, user_id=user_id).first()
    if mem:
        db.session.delete(mem)
        db.session.commit()
    return jsonify({'success': True})

# ==========================================
# MEMBER 1: EMAIL MODULE ROUTES (SHARED DB)
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
        query = Email.query.filter_by(sender_id=user.id, folder='sent')
    elif folder == 'trash':
        query = Email.query.filter_by(folder='trash')
    else: # inbox
        query = Email.query.filter(Email.recipient_email.ilike(f'%{user.email}%'), Email.folder == 'inbox')

    if search:
        query = query.filter((Email.subject.ilike(f'%{search}%')) | (Email.body.ilike(f'%{search}%')))

    emails = query.order_by(Email.created_at.desc()).all()
    res = []
    for e in emails:
        res.append({
            'id': e.id,
            'sender_name': e.sender.name if e.sender else 'System',
            'sender_email': e.sender.email if e.sender else '',
            'recipient_email': e.recipient_email,
            'subject': e.subject,
            'body': e.body,
            'date': e.created_at.strftime('%b %d, %I:%M %p'),
            'is_starred': e.is_starred,
            'is_important': e.is_important
        })
    return jsonify(res)

@app.route('/api/emails/send', methods=['POST'])
def send_email():
    user = get_current_user()
    recipient = request.form.get('recipient')
    subject = request.form.get('subject') or '(No Subject)'
    body = request.form.get('body')

    # Save sent email
    sent_mail = Email(sender_id=user.id, recipient_email=recipient, subject=subject, body=body, folder='sent')
    # Save inbox copy for recipient
    inbox_mail = Email(sender_id=user.id, recipient_email=recipient, subject=subject, body=body, folder='inbox')

    db.session.add_all([sent_mail, inbox_mail])
    db.session.commit()
    return jsonify({'success': True})

# ==========================================
# SOCKET.IO REAL-TIME EVENTS (MEMBER 2)
# ==========================================

@socketio.on('connect')
def on_connect():
    user = get_current_user()
    if user:
        user.is_online = True
        db.session.commit()
        emit('status_change', {'user_id': user.id, 'is_online': True}, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    user = get_current_user()
    if user:
        user.is_online = False
        db.session.commit()
        emit('status_change', {'user_id': user.id, 'is_online': False}, broadcast=True)

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

    msg = Message(conversation_id=conv_id, sender_id=user.id, text=text)
    db.session.add(msg)
    db.session.commit()

    msg_data = msg.to_dict()
    # Broadcast to room
    emit('new_message', msg_data, to=f"room_{conv_id}")
    # Also broadcast notification for users outside the room
    emit('message_notification', {
        'conversation_id': conv_id,
        'sender_id': user.id,
        'sender_name': user.name,
        'text': text
    }, broadcast=True)

@socketio.on('typing')
def on_typing(data):
    user = get_current_user()
    conv_id = data.get('conversation_id')
    emit('user_typing', {
        'conversation_id': conv_id,
        'username': user.name,
        'user_id': user.id
    }, to=f"room_{conv_id}", include_self=False)

@socketio.on('stop_typing')
def on_stop_typing(data):
    conv_id = data.get('conversation_id')
    emit('user_stop_typing', {'conversation_id': conv_id}, to=f"room_{conv_id}", include_self=False)

@socketio.on('mark_read')
def on_mark_read(data):
    user = get_current_user()
    conv_id = data.get('conversation_id')
    mem = ConversationMember.query.filter_by(conversation_id=conv_id, user_id=user.id).first()
    if mem:
        last = Message.query.filter_by(conversation_id=conv_id).order_by(Message.id.desc()).first()
        if last:
            mem.last_read_id = last.id
            db.session.commit()
            emit('read_receipt', {'conversation_id': conv_id, 'read_up_to': last.id}, to=f"room_{conv_id}")

@socketio.on('edit_message')
def on_edit_message(data):
    msg_id = data.get('message_id')
    new_text = data.get('text', '').strip()
    msg = Message.query.get(msg_id)
    if msg and not msg.is_deleted:
        msg.text = new_text
        msg.is_edited = True
        db.session.commit()
        emit('message_edited', {'id': msg.id, 'conversation_id': msg.conversation_id, 'text': new_text}, to=f"room_{msg.conversation_id}")

@socketio.on('delete_message')
def on_delete_message(data):
    msg_id = data.get('message_id')
    msg = Message.query.get(msg_id)
    if msg:
        msg.is_deleted = True
        db.session.commit()
        emit('message_deleted', {'id': msg.id, 'conversation_id': msg.conversation_id}, to=f"room_{msg.conversation_id}")

# Create database tables automatically
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    print("Server running at http://127.0.0.1:5000")
    socketio.run(app, debug=True, host='127.0.0.1', port=5000)
