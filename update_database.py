<<<<<<< HEAD
from app import app
from extensions import db

with app.app_context():
    with db.engine.connect() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE emails ADD COLUMN is_important BOOLEAN DEFAULT 0"
        )
        connection.commit()

=======
from app import app
from extensions import db

with app.app_context():
    with db.engine.connect() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE emails ADD COLUMN is_important BOOLEAN DEFAULT 0"
        )
        connection.commit()

>>>>>>> friend/main
print("Database updated successfully!")