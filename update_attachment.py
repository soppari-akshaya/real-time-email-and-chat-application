
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

        if 'attachment' not in columns:

            connection.exec_driver_sql(
                "ALTER TABLE emails ADD COLUMN attachment VARCHAR(255)"
            )

            connection.commit()

            print("Attachment column added successfully!")

        else:
            print("Attachment column already exists!")
