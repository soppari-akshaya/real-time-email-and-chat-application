from app import app
from extensions import db

with app.app_context():
    with db.engine.connect() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE emails ADD COLUMN is_important BOOLEAN DEFAULT 0"
        )
        connection.commit()

print("Database updated successfully!")