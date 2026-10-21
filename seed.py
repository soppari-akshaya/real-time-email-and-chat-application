from app import app
from models import db, User, Conversation, ConversationMember, Message, Email

with app.app_context():
    # Reset database
    db.drop_all()
    db.create_all()

    # 1. Add simple users (no passwords needed)
    u1 = User(name='Alice', email='alice@college.edu')
    u2 = User(name='Bob', email='bob@college.edu')
    u3 = User(name='Charlie', email='charlie@college.edu')
    db.session.add_all([u1, u2, u3])
    db.session.commit()

    # 2. Add 1-to-1 chat between Alice and Bob
    conv1 = Conversation(is_group=False)
    db.session.add(conv1)
    db.session.flush()

    m1 = ConversationMember(conversation_id=conv1.id, user_id=u1.id, is_admin=True)
    m2 = ConversationMember(conversation_id=conv1.id, user_id=u2.id, is_admin=False)
    db.session.add_all([m1, m2])

    msg1 = Message(conversation_id=conv1.id, sender_id=u1.id, text="Hi Bob, have you started Module 2?")
    msg2 = Message(conversation_id=conv1.id, sender_id=u2.id, text="Hey Alice! Yes, the real-time chat is working.")
    db.session.add_all([msg1, msg2])

    # 3. Add Group Chat "Project Group"
    grp = Conversation(is_group=True, name="Project Team")
    db.session.add(grp)
    db.session.flush()

    gm1 = ConversationMember(conversation_id=grp.id, user_id=u1.id, is_admin=True)
    gm2 = ConversationMember(conversation_id=grp.id, user_id=u2.id, is_admin=False)
    gm3 = ConversationMember(conversation_id=grp.id, user_id=u3.id, is_admin=False)
    db.session.add_all([gm1, gm2, gm3])

    gmsg = Message(conversation_id=grp.id, sender_id=u1.id, text="Welcome everyone to our project chat!")
    db.session.add(gmsg)

    # 4. Add Sample Emails for Member 1
    e1 = Email(sender_id=u2.id, recipient_email='alice@college.edu', subject='Project Presentation Slides', body='Hi Alice,\nI uploaded the slides for tomorrow.\n- Bob', folder='inbox', is_starred=True)
    e2 = Email(sender_id=u1.id, recipient_email='bob@college.edu', subject='Database Schema Updated', body='Bob,\nThe shared database schema is ready for both members.\n- Alice', folder='sent')
    db.session.add_all([e1, e2])

    db.session.commit()
    print("Database seeded with simple sample users and chats!")
