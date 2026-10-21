import os
from flask import Flask, session
from flask_socketio import SocketIO
from config import Config
from models import db, User
from routes import auth_bp, chat_bp, email_bp, admin_bp
from sockets.chat_events import register_socket_events

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_user():
        current_user = None
        if 'user_id' in session:
            current_user = User.query.get(session['user_id'])
        return dict(current_user=current_user)

    with app.app_context():
        db.create_all()

    return app

app = create_app()
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    manage_session=False
)
register_socket_events(socketio)

if __name__ == '__main__':
    print("🚀 Starting OmniSync Email & Real-Time Chat server on http://127.0.0.1:5000")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
