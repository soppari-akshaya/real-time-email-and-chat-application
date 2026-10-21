import os
from datetime import datetime, timedelta
from app import create_app
from models import db, User, Conversation, ConversationMember, Message, Email, EmailAttachment

app = create_app()

def seed_database():
    with app.app_context():
        # Clear existing tables
        db.drop_all()
        db.create_all()
        print("Cleared and recreated database tables.")

        now = datetime.utcnow()

        # 1. Create Users
        users_info = [
            {
                'username': 'alice',
                'email': 'alice@omnisync.com',
                'password': 'password123',
                'bio': 'Full Stack Developer | Coffee enthusiast ☕',
                'role': 'admin',
                'avatar_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=alice'
            },
            {
                'username': 'bob',
                'email': 'bob@omnisync.com',
                'password': 'password123',
                'bio': 'Frontend Specialist & Vue/React Hacker 💻',
                'role': 'user',
                'avatar_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=bob'
            },
            {
                'username': 'charlie',
                'email': 'charlie@omnisync.com',
                'password': 'password123',
                'bio': 'UI/UX Designer | Pixel perfectionist 🎨',
                'role': 'user',
                'avatar_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=charlie'
            },
            {
                'username': 'diana',
                'email': 'diana@omnisync.com',
                'password': 'password123',
                'bio': 'QA Engineer & Test Automation Wizard 🛡️',
                'role': 'user',
                'avatar_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=diana'
            },
            {
                'username': 'admin',
                'email': 'admin@omnisync.com',
                'password': 'admin123',
                'bio': 'System Administrator & DevOps Guru ⚙️',
                'role': 'admin',
                'avatar_url': 'https://api.dicebear.com/7.x/bottts/svg?seed=admin'
            }
        ]

        users = {}
        for u in users_info:
            user = User(
                username=u['username'],
                email=u['email'],
                bio=u['bio'],
                role=u['role'],
                avatar_url=u['avatar_url'],
                is_online=False,
                last_seen=now - timedelta(minutes=15)
            )
            user.set_password(u['password'])
            db.session.add(user)
            users[u['username']] = user

        db.session.commit()
        print("Seeded 5 demo users.")

        # 2. Create 1-to-1 Conversation (Alice & Bob)
        conv1 = Conversation(is_group=False, created_by_id=users['alice'].id, updated_at=now - timedelta(minutes=5))
        db.session.add(conv1)
        db.session.flush()

        m_a1 = ConversationMember(conversation_id=conv1.id, user_id=users['alice'].id, is_admin=True)
        m_b1 = ConversationMember(conversation_id=conv1.id, user_id=users['bob'].id, is_admin=False)
        db.session.add_all([m_a1, m_b1])

        messages_conv1 = [
            (users['bob'], "Hey Alice! Have you checked out the real-time chat module?", now - timedelta(hours=2)),
            (users['alice'], "Hey Bob! Yes, typing indicators, read receipts, and file uploads are running smooth!", now - timedelta(hours=1, minutes=45)),
            (users['bob'], "Awesome. I tested editing and deleting messages too - works seamlessly.", now - timedelta(hours=1)),
            (users['alice'], "Let's test sending group files and verify delivery status next.", now - timedelta(minutes=10))
        ]

        for sender, text, ts in messages_conv1:
            msg = Message(
                conversation_id=conv1.id,
                sender_id=sender.id,
                text=text,
                message_type='text',
                created_at=ts,
                updated_at=ts
            )
            db.session.add(msg)
            db.session.flush()

        # Update last read
        m_a1.last_read_message_id = msg.id
        m_b1.last_read_message_id = msg.id

        # 3. Create Group Conversation ("Core Engineering 🚀")
        group_conv = Conversation(
            is_group=True,
            name="Core Engineering 🚀",
            description="Official developer channel for architecture, chat sync, and releases.",
            avatar_url="https://api.dicebear.com/7.x/identicon/svg?seed=Engineering",
            created_by_id=users['alice'].id,
            updated_at=now - timedelta(minutes=2)
        )
        db.session.add(group_conv)
        db.session.flush()

        # Members: Alice (Admin), Bob, Charlie, Diana
        gm_alice = ConversationMember(conversation_id=group_conv.id, user_id=users['alice'].id, is_admin=True)
        gm_bob = ConversationMember(conversation_id=group_conv.id, user_id=users['bob'].id, is_admin=False)
        gm_charlie = ConversationMember(conversation_id=group_conv.id, user_id=users['charlie'].id, is_admin=False)
        gm_diana = ConversationMember(conversation_id=group_conv.id, user_id=users['diana'].id, is_admin=False)
        db.session.add_all([gm_alice, gm_bob, gm_charlie, gm_diana])

        group_msgs = [
            (users['alice'], "Welcome everyone to Core Engineering!", now - timedelta(hours=5)),
            (users['charlie'], "Hey team! The UI styling with glassmorphism and dark mode is looking sleek! ✨", now - timedelta(hours=4)),
            (users['diana'], "All test suites for one-to-one messaging and group member management passed with zero errors.", now - timedelta(hours=3)),
            (users['bob'], "I'm pushing the latest responsive fixes for mobile views right now.", now - timedelta(hours=1, minutes=20)),
            (users['alice'], "Great work team. Don't forget you can share files, edit messages, and toggle dark mode in the header.", now - timedelta(minutes=15))
        ]

        for sender, text, ts in group_msgs:
            gmsg = Message(
                conversation_id=group_conv.id,
                sender_id=sender.id,
                text=text,
                message_type='text',
                created_at=ts,
                updated_at=ts
            )
            db.session.add(gmsg)
            db.session.flush()

        gm_alice.last_read_message_id = gmsg.id

        # 4. Create sample emails for Member 1 integration
        emails_sample = [
            {
                'sender': users['bob'],
                'recipient_emails': 'alice@omnisync.com',
                'subject': 'Sprint Review & Architecture Sign-Off',
                'body': 'Hi Alice,\n\nPlease review the attached specifications for the unified database schema. Both Member 1 (Email) and Member 2 (Chat) modules share the authentication layer and SQLite database.\n\nBest regards,\nBob',
                'folder': 'inbox',
                'is_starred': True,
                'is_important': True,
                'is_read': False,
                'labels': 'Work, Urgent',
                'created_at': now - timedelta(hours=6)
            },
            {
                'sender': users['charlie'],
                'recipient_emails': 'alice@omnisync.com',
                'subject': 'Design System & Dark Theme Tokens updated',
                'body': 'Alice,\n\nI have polished the CSS theme variables. Both dark and light themes now feature smooth 250ms transitions and crisp typography.\n\nCheers,\nCharlie',
                'folder': 'inbox',
                'is_starred': False,
                'is_important': True,
                'is_read': True,
                'labels': 'Design',
                'created_at': now - timedelta(days=1)
            },
            {
                'sender': users['alice'],
                'recipient_emails': 'bob@omnisync.com, charlie@omnisync.com',
                'subject': 'Weekly Sync Notes & Chat Module Deliverables',
                'body': 'Team,\n\nHere are the highlights from today\'s review:\n- 1-to-1 & Group chat complete\n- Real-time typing indicators active\n- Read receipts and message delivery statuses verified\n- File attachment sharing tested\n\nThanks everyone!',
                'folder': 'sent',
                'is_starred': True,
                'is_important': False,
                'is_read': True,
                'labels': 'Work',
                'created_at': now - timedelta(hours=8)
            },
            {
                'sender': users['alice'],
                'recipient_emails': 'team@omnisync.com',
                'subject': 'Draft: Quarterly Roadmap Preview',
                'body': 'Upcoming initiatives including mobile notifications and advanced message search filters...',
                'folder': 'drafts',
                'is_starred': False,
                'is_important': False,
                'is_read': True,
                'labels': 'Draft',
                'created_at': now - timedelta(days=2)
            }
        ]

        for e_info in emails_sample:
            email_entry = Email(
                sender_id=e_info['sender'].id,
                recipient_emails=e_info['recipient_emails'],
                subject=e_info['subject'],
                body=e_info['body'],
                folder=e_info['folder'],
                is_starred=e_info['is_starred'],
                is_important=e_info['is_important'],
                is_read=e_info['is_read'],
                labels=e_info['labels'],
                created_at=e_info['created_at']
            )
            db.session.add(email_entry)

        db.session.commit()
        print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
