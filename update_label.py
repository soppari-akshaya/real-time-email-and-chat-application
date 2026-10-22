
from app import app
from extensions import db

with app.app_context():
    with db.engine.connect() as connection:
        columns = [
            row[1]
            for row in connection.exec_driver_sql(
                "PRAGMA table_info(emails)"
            ).fetchall()
        ]

        if 'label' not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE emails ADD COLUMN label VARCHAR(50) DEFAULT 'General'"
            )
            connection.commit()
            print("Label column added successfully!")
        else:
            print("Label column already exists!")
