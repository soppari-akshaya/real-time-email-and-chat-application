import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import get_user_by_email, get_user_by_id, create_user, set_user_online
from utils import get_current_user
from extensions import socketio

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    return redirect(url_for('chat.chat_page'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register_page():
    return redirect(url_for('chat.chat_page'))

@auth_bp.route('/logout')
def logout():
    return redirect(url_for('chat.chat_page'))

@auth_bp.route('/quick-login/<int:user_id>')
def quick_login(user_id):
    user = get_user_by_id(user_id)
    if user:
        session['user_id'] = user['id']
        set_user_online(user['id'], True)
        socketio.emit('status_change', {'user_id': user['id'], 'is_online': True})
        flash(f'Quick logged in as {user["name"]} ({user["email"]})', 'success')
    return redirect(url_for('chat.chat_page'))

@auth_bp.route('/switch-user/<int:user_id>')
def switch_user(user_id):
    user = get_user_by_id(user_id)
    if user:
        session['user_id'] = user['id']
        set_user_online(user['id'], True)
        socketio.emit('status_change', {'user_id': user['id'], 'is_online': True})
    referrer = request.referrer or url_for('chat.chat_page')
    return redirect(referrer)
