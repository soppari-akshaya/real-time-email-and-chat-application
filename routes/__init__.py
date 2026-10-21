from routes.auth import auth_bp
from routes.chat import chat_bp
from routes.email import email_bp
from routes.admin import admin_bp

__all__ = ['auth_bp', 'chat_bp', 'email_bp', 'admin_bp']
