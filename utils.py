from functools import wraps
from flask import session, request, redirect, url_for, jsonify
from models import get_user_by_id, get_all_users

def get_current_user():
    user_id = session.get('user_id')
    user = get_user_by_id(user_id) if user_id else None
    if not user:
        all_u = get_all_users()
        if all_u:
            user = all_u[0]
            session['user_id'] = user['id']
    return user

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'No users available'}), 404
            return redirect(url_for('chat.chat_page'))
        return f(*args, **kwargs)
    return decorated_function
