from app import app
from extensions import db
from email_module.models import User

with app.app_context():

    if not User.query.filter_by(email="user1@gmail.com").first():
        user1 = User(
            name="User One",
            email="user1@gmail.com",
            password="test123"
        )
        db.session.add(user1)

    if not User.query.filter_by(email="user2@gmail.com").first():
        user2 = User(
            name="User Two",
            email="user2@gmail.com",
            password="test123"
        )
        db.session.add(user2)

    db.session.commit()

print("Test users created successfully!")