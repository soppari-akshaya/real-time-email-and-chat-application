from flask_socketio import emit, join_room, leave_room
from extensions import socketio
from utils import get_current_user
from models import (
    set_user_online, create_message, edit_message as db_edit_message,
    delete_message as db_delete_message, mark_conversation_read, mark_messages_delivered
)

def register_socket_events(socketio_instance):

    @socketio_instance.on('connect')
    def handle_connect():
        user = get_current_user()
        if user:
            set_user_online(user['id'], True)
            mark_messages_delivered(user['id'])
            emit('status_change', {'user_id': user['id'], 'is_online': True}, broadcast=True)
            emit('messages_delivered', {'recipient_id': user['id']}, broadcast=True)

    @socketio_instance.on('disconnect')
    def handle_disconnect():
        user = get_current_user()
        if user:
            set_user_online(user['id'], False)
            emit('status_change', {'user_id': user['id'], 'is_online': False}, broadcast=True)

    @socketio_instance.on('join_room')
    def handle_join_room(data):
        join_room(f"room_{data.get('conversation_id')}")

    @socketio_instance.on('leave_room')
    def handle_leave_room(data):
        leave_room(f"room_{data.get('conversation_id')}")

    @socketio_instance.on('send_message')
    def handle_send_message(data):
        user = get_current_user()
        if not user:
            return

        conv_id = data.get('conversation_id')
        text = data.get('text', '').strip()

        if not conv_id or not text:
            return

        formatted = create_message(conv_id, user['id'], user['name'], text)
        emit('new_message', formatted, to=f"room_{conv_id}")
        emit('message_notification', {
            'message_id': str(formatted['id']),
            'conversation_id': str(conv_id),
            'sender_id': user['id'],
            'sender_name': user['name'],
            'text': text
        }, broadcast=True)

    @socketio_instance.on('typing')
    def handle_typing(data):
        user = get_current_user()
        if not user:
            return
        conv_id = data.get('conversation_id')
        emit('user_typing', {
            'conversation_id': conv_id,
            'username': user['name'],
            'user_id': user['id']
        }, to=f"room_{conv_id}", include_self=False)

    @socketio_instance.on('stop_typing')
    def handle_stop_typing(data):
        user = get_current_user()
        conv_id = data.get('conversation_id')
        emit('user_stop_typing', {
            'conversation_id': conv_id,
            'user_id': user['id'] if user else None
        }, to=f"room_{conv_id}", include_self=False)

    @socketio_instance.on('mark_read')
    def handle_mark_read(data):
        user = get_current_user()
        conv_id = data.get('conversation_id')
        if conv_id and user:
            mark_conversation_read(conv_id, user['id'])
            emit('read_receipt', {
                'conversation_id': conv_id,
                'reader_id': user['id'],
                'reader_name': user['name']
            }, to=f"room_{conv_id}")

    @socketio_instance.on('edit_message')
    def handle_edit_message(data):
        msg_id = data.get('message_id')
        new_text = data.get('text', '').strip()
        if msg_id and new_text:
            updated = db_edit_message(int(msg_id), new_text)
            if updated:
                emit('message_edited', {
                    'id': str(updated['id']),
                    'conversation_id': str(updated['conversation_id']),
                    'text': new_text
                }, to=f"room_{updated['conversation_id']}")

    @socketio_instance.on('delete_message')
    def handle_delete_message(data):
        msg_id = data.get('message_id')
        if msg_id:
            deleted = db_delete_message(int(msg_id))
            if deleted:
                emit('message_deleted', {
                    'id': str(deleted['id']),
                    'conversation_id': str(deleted['conversation_id'])
                }, to=f"room_{deleted['conversation_id']}")
