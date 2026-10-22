
from flask import Flask, redirect, url_for
from flask_login import LoginManager

from extensions import db
from email_module import email_bp
from email_module.models import Email, User
from auth_module import auth_bp

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///email_chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize Database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'


# Load Logged-in User
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Register Blueprints
app.register_blueprint(email_bp)
app.register_blueprint(auth_bp)


@app.route('/')
def home():
    return redirect(url_for('auth.login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)
