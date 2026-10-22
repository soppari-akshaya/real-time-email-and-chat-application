from flask import Blueprint, request, jsonify
from models import get_all_users
from utils import get_current_user, login_required

user_bp = Blueprint('user', __name__)

@user_bp.route('/api/users')
@login_required
def list_registered_users():
    cur = get_current_user()
    q = request.args.get('q', '').strip()
    all_users = get_all_users(query=q if q else None)
    return jsonify([{
        'id': u['id'],
        'name': u['name'],
        'email': u['email'],
        'is_online': bool(u['is_online']),
        'is_me': (cur and u['id'] == cur['id'])
    } for u in all_users])
