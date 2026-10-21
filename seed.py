from datetime import datetime
from db import users, conversations, messages, emails

def seed_mongodb():
    # 1. Clear existing collections
    users.drop()
    conversations.drop()
    messages.drop()
    emails.drop()

    now = datetime.utcnow()

    # 2. Insert simple users (no passwords needed)
    users_data = [
        {'id': 1, 'name': 'Alice', 'email': 'alice@college.edu', 'is_online': False},
        {'id': 2, 'name': 'Bob', 'email': 'bob@college.edu', 'is_online': False},
        {'id': 3, 'name': 'Charlie', 'email': 'charlie@college.edu', 'is_online': False}
    ]
    users.insert_many(users_data)
    print("Added users to MongoDB: Alice, Bob, Charlie")

    # 3. Create 1-to-1 conversation between Alice and Bob
    conv1 = {
        'is_group': False,
        'name': None,
        'members': [
            {'user_id': 1, 'is_admin': True, 'last_read_time': now},
            {'user_id': 2, 'is_admin': False, 'last_read_time': now}
        ],
        'created_at': now
    }
    conv1_id = str(conversations.insert_one(conv1).inserted_id)

    # 4. Insert messages in conversation 1
    messages.insert_many([
        {
            'conversation_id': conv1_id,
            'sender_id': 1,
            'sender_name': 'Alice',
            'text': 'Hi Bob, have you started Module 2?',
            'file_url': None,
            'file_name': None,
            'is_edited': False,
            'is_deleted': False,
            'created_at': now
        },
        {
            'conversation_id': conv1_id,
            'sender_id': 2,
            'sender_name': 'Bob',
            'text': 'Hey Alice! Yes, the real-time chat with MongoDB is working.',
            'file_url': None,
            'file_name': None,
            'is_edited': False,
            'is_deleted': False,
            'created_at': now
        }
    ])

    # 5. Create Group Chat "Project Team"
    grp = {
        'is_group': True,
        'name': 'Project Team',
        'members': [
            {'user_id': 1, 'is_admin': True, 'last_read_time': now},
            {'user_id': 2, 'is_admin': False, 'last_read_time': now},
            {'user_id': 3, 'is_admin': False, 'last_read_time': now}
        ],
        'created_at': now
    }
    grp_id = str(conversations.insert_one(grp).inserted_id)

    messages.insert_one({
        'conversation_id': grp_id,
        'sender_id': 1,
        'sender_name': 'Alice',
        'text': 'Welcome everyone to our project chat on MongoDB!',
        'file_url': None,
        'file_name': None,
        'is_edited': False,
        'is_deleted': False,
        'created_at': now
    })

    # 6. Sample Emails for Member 1 Integration
    emails.insert_many([
        {
            'sender_id': 2,
            'sender_name': 'Bob',
            'sender_email': 'bob@college.edu',
            'recipient_email': 'alice@college.edu',
            'subject': 'Project Presentation Slides',
            'body': 'Hi Alice,\nI uploaded the slides for tomorrow.\n- Bob',
            'folder': 'inbox',
            'is_starred': True,
            'is_important': True,
            'created_at': now
        },
        {
            'sender_id': 1,
            'sender_name': 'Alice',
            'sender_email': 'alice@college.edu',
            'recipient_email': 'bob@college.edu',
            'subject': 'MongoDB Database Connected',
            'body': 'Bob,\nThe shared MongoDB database is ready for both members.\n- Alice',
            'folder': 'sent',
            'is_starred': False,
            'is_important': False,
            'created_at': now
        }
    ])

    print("MongoDB successfully seeded with sample data!")

if __name__ == '__main__':
    seed_mongodb()
