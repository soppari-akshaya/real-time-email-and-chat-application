from datetime import datetime
from flask import request, session
from flask_socketio import emit, join_room, leave_room
from models import db, User, Conversation, ConversationMember, Message, MessageStatus

# Active socket mappings: user_id -> set of socket session IDs
online_user_sockets = {}

def register_socket_events(socketio):
    @socketio.on('connect')
    def handle_connect():
        user_id = session.get('user_id')
        if not user_id:
            return False  # Reject unauthenticated socket connections

        sid = request.sid
        if user_id not in online_user_sockets:
            online_user_sockets[user_id] = set()
        online_user_sockets[user_id].add(sid)

        # Update user status to online
        user = User.query.get(user_id)
        if user:
            user.is_online = True
            db.session.commit()
            emit('user_status_changed', {
                'user_id': user.id,
                'is_online': True,
                'last_seen': user.last_seen.isoformat() if user.last_seen else None
            }, broadcast=True)

        # Join personal user room for direct notifications
        join_room(f"user_{user_id}")

    @socketio.on('disconnect')
    def handle_disconnect():
        user_id = session.get('user_id')
        sid = request.sid
        if user_id and user_id in online_user_sockets:
            online_user_sockets[user_id].discard(sid)
            if not online_user_sockets[user_id]:
                del online_user_sockets[user_id]
                user = User.query.get(user_id)
                if user:
                    user.is_online = False
                    user.last_seen = datetime.utcnow()
                    db.session.commit()
                    emit('user_status_changed', {
                        'user_id': user.id,
                        'is_online': False,
                        'last_seen': user.last_seen.isoformat()
                    }, broadcast=True)

    @socketio.on('join_conversation')
    def handle_join_conversation(data):
        conv_id = data.get('conversation_id')
        user_id = session.get('user_id')
        if not conv_id or not user_id:
            return

        room_name = f"conv_{conv_id}"
        join_room(room_name)

        # Mark read on join
        membership = ConversationMember.query.filter_by(
            conversation_id=conv_id,
            user_id=user_id
        ).first()

        if membership:
            last_msg = Message.query.filter_by(conversation_id=conv_id).order_by(Message.id.desc()).first()
            if last_msg:
                membership.last_read_message_id = last_msg.id
                db.session.commit()

                # Broadcast read receipts to the room
                emit('messages_read', {
                    'conversation_id': conv_id,
                    'reader_id': user_id,
                    'last_read_message_id': last_msg.id
                }, to=room_name)

    @socketio.on('leave_conversation')
    def handle_leave_conversation(data):
        conv_id = data.get('conversation_id')
        if conv_id:
            leave_room(f"conv_{conv_id}")

    @socketio.on('send_message')
    def handle_send_message(data):
        user_id = session.get('user_id')
        if not user_id:
            return

        conv_id = data.get('conversation_id')
        text = data.get('text', '').strip()
        msg_type = data.get('message_type', 'text')
        file_path = data.get('file_path')
        file_name = data.get('file_name')
        file_size = data.get('file_size')

        if not conv_id or (not text and not file_path):
            return

        conv = Conversation.query.get(conv_id)
        if not conv:
            return

        membership = conv.members.filter_by(user_id=user_id).first()
        if not membership:
            return

        # Create message in DB
        new_msg = Message(
            conversation_id=conv_id,
            sender_id=user_id,
            text=text,
            message_type=msg_type,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size
        )
        conv.updated_at = datetime.utcnow()
        db.session.add(new_msg)
        db.session.commit()

        # Update sender's last read message id
        membership.last_read_message_id = new_msg.id
        db.session.commit()

        msg_dict = new_msg.to_dict(current_user_id=user_id)

        # Broadcast to conversation room
        room_name = f"conv_{conv_id}"
        emit('new_message', msg_dict, to=room_name)

        # Emit notifications to all members not currently in the room
        all_members = conv.members.all()
        sender_user = User.query.get(user_id)
        sender_name = sender_user.username if sender_user else "Someone"

        for m in all_members:
            if m.user_id != user_id:
                emit('notification', {
                    'type': 'chat_message',
                    'conversation_id': conv_id,
                    'sender_id': user_id,
                    'sender_name': sender_name,
                    'text': text if text else f"Sent an attachment: {file_name or 'file'}",
                    'conversation_name': conv.get_display_name(m.user_id)
                }, to=f"user_{m.user_id}")

    @socketio.on('typing')
    def handle_typing(data):
        user_id = session.get('user_id')
        conv_id = data.get('conversation_id')
        if user_id and conv_id:
            user = User.query.get(user_id)
            emit('user_typing', {
                'user_id': user_id,
                'username': user.username if user else 'User',
                'conversation_id': conv_id
            }, to=f"conv_{conv_id}", include_self=False)

    @socketio.on('stop_typing')
    def handle_stop_typing(data):
        user_id = session.get('user_id')
        conv_id = data.get('conversation_id')
        if user_id and conv_id:
            emit('user_stop_typing', {
                'user_id': user_id,
                'conversation_id': conv_id
            }, to=f"conv_{conv_id}", include_self=False)

    @socketio.on('mark_read')
    def handle_mark_read(data):
        user_id = session.get('user_id')
        conv_id = data.get('conversation_id')
        if not user_id or not conv_id:
            return

        membership = ConversationMember.query.filter_by(
            conversation_id=conv_id,
            user_id=user_id
        ).first()

        if membership:
            last_msg = Message.query.filter_by(conversation_id=conv_id).order_by(Message.id.desc()).first()
            if last_msg:
                membership.last_read_message_id = last_msg.id
                db.session.commit()

                emit('messages_read', {
                    'conversation_id': conv_id,
                    'reader_id': user_id,
                    'last_read_message_id': last_msg.id
                }, to=f"conv_{conv_id}")

    @socketio.on('edit_message')
    def handle_edit_message(data):
        user_id = session.get('user_id')
        msg_id = data.get('message_id')
        new_text = data.get('text', '').strip()

        if not user_id or not msg_id or not new_text:
            return

        msg = Message.query.get(msg_id)
        if msg and msg.sender_id == user_id and not msg.is_deleted:
            msg.text = new_text
            msg.is_edited = True
            msg.updated_at = datetime.utcnow()
            db.session.commit()

            emit('message_edited', msg.to_dict(current_user_id=user_id), to=f"conv_{msg.conversation_id}")

    @socketio.on('delete_message')
    def handle_delete_message(data):
        user_id = session.get('user_id')
        msg_id = data.get('message_id')

        if not user_id or not msg_id:
            return

        msg = Message.query.get(msg_id)
        if msg and msg.sender_id == user_id:
            msg.is_deleted = True
            msg.text = "This message was deleted"
            msg.updated_at = datetime.utcnow()
            db.session.commit()

            emit('message_deleted', {
                'message_id': msg.id,
                'conversation_id': msg.conversation_id,
                'is_deleted': True,
                'text': "This message was deleted"
            }, to=f"conv_{msg.conversation_id}")
