import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from werkzeug.utils import secure_filename
from models import db, User

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('chat.chat_view'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        bio = request.form.get('bio', 'Hey there! I am using OmniSync.')

        if not username or not email or not password:
            flash('Username, email, and password are required.', 'danger')
            return render_template('register.html', username=username, email=email)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', username=username, email=email)

        if User.query.filter_by(username=username).first():
            flash('Username is already taken.', 'danger')
            return render_template('register.html', username=username, email=email)

        if User.query.filter_by(email=email).first():
            flash('Email is already registered.', 'danger')
            return render_template('register.html', username=username, email=email)

        avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={username}"
        new_user = User(
            username=username,
            email=email,
            bio=bio,
            avatar_url=avatar_url,
            role='admin' if User.query.count() == 0 else 'user'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session['username'] = new_user.username
        flash('Account registered successfully! Welcome aboard.', 'success')
        return redirect(url_for('chat.chat_view'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('chat.chat_view'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('chat.chat_view'))
        else:
            flash('Invalid username/email or password.', 'danger')

    # Provide demo users for one-click testing
    demo_users = User.query.limit(4).all()
    return render_template('login.html', demo_users=demo_users)

@auth_bp.route('/quick-login/<int:user_id>')
def quick_login(user_id):
    """Convenient switch between users for demoing real-time chat between tabs"""
    user = User.query.get_or_404(user_id)
    session['user_id'] = user.id
    session['username'] = user.username
    flash(f'Switched to {user.username} (Demo Account)', 'info')
    return redirect(url_for('chat.chat_view'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    if request.method == 'POST':
        user.bio = request.form.get('bio', user.bio).strip()
        new_password = request.form.get('new_password', '').strip()
        
        # Profile picture upload
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '':
                filename = secure_filename(f"avatar_{user.id}_{file.filename}")
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                user.avatar_url = url_for('static', filename=f'uploads/{filename}')

        if new_password:
            user.set_password(new_password)
            flash('Password updated successfully.', 'success')

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('profile.html', user=user)

@auth_bp.route('/api/users/search')
@login_required
def search_users():
    query = request.args.get('q', '').strip()
    current_uid = session.get('user_id')
    
    users_query = User.query.filter(User.id != current_uid)
    if query:
        users_query = users_query.filter(
            (User.username.ilike(f'%{query}%')) | (User.email.ilike(f'%{query}%'))
        )
    users = users_query.limit(20).all()
    return jsonify([u.to_dict() for u in users])
