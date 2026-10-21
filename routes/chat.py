import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, current_app, url_for
from werkzeug.utils import secure_filename
from models import db, User, Conversation, ConversationMember, Message, MessageStatus
from routes.auth import login_required, get_current_user

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/')
@chat_bp.route('/chat')
@login_required
def chat_view():
    user = get_current_user()
    all_users = User.query.filter(User.id != user.id).all()
    return render_template('chat.html', current_user=user, all_users=all_users)

@chat_bp.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    user_id = session['user_id']
    memberships = ConversationMember.query.filter_by(user_id=user_id).all()
    conv_ids = [m.conversation_id for m in memberships]
    
    conversations = Conversation.query.filter(Conversation.id.in_(conv_ids))\
        .order_by(Conversation.updated_at.desc()).all()
    
    return jsonify([c.to_dict(current_user_id=user_id) for c in conversations])

@chat_bp.route('/api/conversations/direct/<int:other_user_id>', methods=['POST'])
@login_required
def get_or_create_direct_chat(other_user_id):
    current_uid = session['user_id']
    if current_uid == other_user_id:
        return jsonify({'error': 'Cannot start conversation with yourself'}), 400

    other_user = User.query.get_or_404(other_user_id)

    # Check if a 1-to-1 conversation already exists
    convs = Conversation.query.filter_by(is_group=False).all()
    for conv in convs:
        member_ids = {m.user_id for m in conv.members.all()}
        if member_ids == {current_uid, other_user_id}:
            return jsonify(conv.to_dict(current_user_id=current_uid))

    # Create new 1-on-1 conversation
    new_conv = Conversation(
        is_group=False,
        created_by_id=current_uid
    )
    db.session.add(new_conv)
    db.session.flush()

    m1 = ConversationMember(conversation_id=new_conv.id, user_id=current_uid, is_admin=True)
    m2 = ConversationMember(conversation_id=new_conv.id, user_id=other_user_id, is_admin=False)
    db.session.add_all([m1, m2])
    db.session.commit()

    return jsonify(new_conv.to_dict(current_user_id=current_uid)), 201

@chat_bp.route('/api/conversations/group', methods=['POST'])
@login_required
def create_group():
    current_uid = session['user_id']
    data = request.get_json() or {}
    
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    member_ids = data.get('member_ids', [])

    if not name:
        return jsonify({'error': 'Group name is required'}), 400

    new_conv = Conversation(
        is_group=True,
        name=name,
        description=description,
        avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={name}",
        created_by_id=current_uid
    )
    db.session.add(new_conv)
    db.session.flush()

    # Add creator as admin
    creator_member = ConversationMember(
        conversation_id=new_conv.id,
        user_id=current_uid,
        is_admin=True
    )
    db.session.add(creator_member)

    # Add selected members
    for uid in member_ids:
        if uid != current_uid and User.query.get(uid):
            db.session.add(ConversationMember(
                conversation_id=new_conv.id,
                user_id=uid,
                is_admin=False
            ))

    # Add welcome message
    welcome_msg = Message(
        conversation_id=new_conv.id,
        sender_id=current_uid,
        text=f"Group '{name}' was created.",
        message_type='text'
    )
    db.session.add(welcome_msg)
    db.session.commit()

    return jsonify(new_conv.to_dict(current_user_id=current_uid)), 201

@chat_bp.route('/api/conversations/<int:conv_id>', methods=['GET'])
@login_required
def get_conversation_details(conv_id):
    current_uid = session['user_id']
    conv = Conversation.query.get_or_404(conv_id)
    
    # Check membership
    my_membership = conv.members.filter_by(user_id=current_uid).first()
    if not my_membership:
        return jsonify({'error': 'Not authorized'}), 403

    members_data = [m.to_dict() for m in conv.members.all()]
    
    res = conv.to_dict(current_user_id=current_uid)
    res['members'] = members_data
    res['is_admin'] = my_membership.is_admin
    return jsonify(res)

@chat_bp.route('/api/conversations/<int:conv_id>/messages', methods=['GET'])
@login_required
def get_messages(conv_id):
    current_uid = session['user_id']
    conv = Conversation.query.get_or_404(conv_id)
    
    membership = conv.members.filter_by(user_id=current_uid).first()
    if not membership:
        return jsonify({'error': 'Not authorized'}), 403

    # Support chat search query
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))

    messages_query = conv.messages
    if query:
        messages_query = messages_query.filter(Message.text.ilike(f'%{query}%'))

    messages = messages_query.order_by(Message.created_at.asc()).all()

    # Automatically mark conversation messages as read when fetched
    last_msg = conv.messages.order_by(Message.id.desc()).first()
    if last_msg and (membership.last_read_message_id or 0) < last_msg.id:
        membership.last_read_message_id = last_msg.id
        db.session.commit()

    return jsonify([m.to_dict(current_user_id=current_uid) for m in messages])

@chat_bp.route('/api/conversations/<int:conv_id>/upload', methods=['POST'])
@login_required
def upload_file(conv_id):
    current_uid = session['user_id']
    conv = Conversation.query.get_or_404(conv_id)
    
    if not conv.members.filter_by(user_id=current_uid).first():
        return jsonify({'error': 'Not authorized'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    original_name = file.filename
    clean_name = secure_filename(f"{int(datetime.utcnow().timestamp())}_{original_name}")
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], clean_name)
    file.save(upload_path)

    file_size = os.path.getsize(upload_path)
    file_ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    
    is_image = file_ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    msg_type = 'image' if is_image else 'file'

    rel_url = url_for('static', filename=f'uploads/{clean_name}')

    new_msg = Message(
        conversation_id=conv_id,
        sender_id=current_uid,
        text=request.form.get('caption', '').strip() or original_name,
        message_type=msg_type,
        file_path=rel_url,
        file_name=original_name,
        file_size=file_size
    )
    conv.updated_at = datetime.utcnow()
    db.session.add(new_msg)
    db.session.commit()

    return jsonify(new_msg.to_dict(current_user_id=current_uid)), 201

@chat_bp.route('/api/conversations/<int:conv_id>/members', methods=['POST'])
@login_required
def add_member(conv_id):
    current_uid = session['user_id']
    conv = Conversation.query.get_or_404(conv_id)
    
    if not conv.is_group:
        return jsonify({'error': 'Cannot add members to direct chat'}), 400

    admin_membership = conv.members.filter_by(user_id=current_uid, is_admin=True).first()
    if not admin_membership:
        return jsonify({'error': 'Only group admins can add members'}), 403

    data = request.get_json() or {}
    user_id = data.get('user_id')
    user_to_add = User.query.get_or_404(user_id)

    if conv.members.filter_by(user_id=user_id).first():
        return jsonify({'error': 'User is already a member'}), 400

    new_member = ConversationMember(conversation_id=conv.id, user_id=user_id, is_admin=False)
    db.session.add(new_member)
    
    # System message
    sys_msg = Message(
        conversation_id=conv.id,
        sender_id=current_uid,
        text=f"Added {user_to_add.username} to the group.",
        message_type='text'
    )
    db.session.add(sys_msg)
    db.session.commit()

    return jsonify({'success': True, 'member': new_member.to_dict()})

@chat_bp.route('/api/conversations/<int:conv_id>/members/<int:user_id>', methods=['DELETE'])
@login_required
def remove_member(conv_id, user_id):
    current_uid = session['user_id']
    conv = Conversation.query.get_or_404(conv_id)
    
    if not conv.is_group:
        return jsonify({'error': 'Invalid conversation type'}), 400

    admin_membership = conv.members.filter_by(user_id=current_uid, is_admin=True).first()
    if not admin_membership and current_uid != user_id:
        return jsonify({'error': 'Permission denied'}), 403

    target_membership = conv.members.filter_by(user_id=user_id).first_or_404()
    target_username = target_membership.user.username if target_membership.user else "User"

    db.session.delete(target_membership)
    
    sys_msg = Message(
        conversation_id=conv.id,
        sender_id=current_uid,
        text=f"{target_username} left or was removed from the group.",
        message_type='text'
    )
    db.session.add(sys_msg)
    db.session.commit()

    return jsonify({'success': True})

@chat_bp.route('/api/conversations/<int:conv_id>/leave', methods=['POST'])
@login_required
def leave_group(conv_id):
    return remove_member(conv_id, session['user_id'])

@chat_bp.route('/api/conversations/<int:conv_id>/read', methods=['POST'])
@login_required
def mark_read(conv_id):
    current_uid = session['user_id']
    membership = ConversationMember.query.filter_by(conversation_id=conv_id, user_id=current_uid).first()
    if membership:
        last_msg = Message.query.filter_by(conversation_id=conv_id).order_by(Message.id.desc()).first()
        if last_msg:
            membership.last_read_message_id = last_msg.id
            db.session.commit()
    return jsonify({'success': True})

@chat_bp.route('/api/messages/<int:msg_id>/edit', methods=['PUT'])
@login_required
def edit_message(msg_id):
    current_uid = session['user_id']
    msg = Message.query.get_or_404(msg_id)
    
    if msg.sender_id != current_uid:
        return jsonify({'error': 'Cannot edit messages from other users'}), 403

    if msg.is_deleted:
        return jsonify({'error': 'Cannot edit deleted message'}), 400

    data = request.get_json() or {}
    new_text = data.get('text', '').strip()
    if not new_text:
        return jsonify({'error': 'Message text cannot be empty'}), 400

    msg.text = new_text
    msg.is_edited = True
    msg.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(msg.to_dict(current_user_id=current_uid))

@chat_bp.route('/api/messages/<int:msg_id>', methods=['DELETE'])
@login_required
def delete_message(msg_id):
    current_uid = session['user_id']
    msg = Message.query.get_or_404(msg_id)
    
    if msg.sender_id != current_uid:
        return jsonify({'error': 'Cannot delete messages from other users'}), 403

    msg.is_deleted = True
    msg.text = "This message was deleted"
    msg.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(msg.to_dict(current_user_id=current_uid))
