import os
from flask import Flask
from database import init_db
from extensions import socketio
from sockets import register_socket_events
from utils import get_current_user
from models import get_all_users
from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp
from routes.user_routes import user_bp

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'workspace-secret-key-2026'
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    init_db()

    @app.context_processor
    def inject_globals():
        return {
            'current_user': get_current_user(),
            'all_users': get_all_users()
        }

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(user_bp)

    socketio.init_app(app, cors_allowed_origins="*")
    register_socket_events(socketio)

    return app

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='127.0.0.1', port=5000, allow_unsafe_werkzeug=True)
