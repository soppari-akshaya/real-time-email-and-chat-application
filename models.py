import sqlite3
from datetime import datetime
from database import get_db

def parse_dt(ts):
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        cleaned = ts.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(cleaned)
        except Exception:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
            try:
                return datetime.strptime(ts, fmt)
            except Exception:
                pass
    return None

def format_timestamp(ts):
    dt = parse_dt(ts)
    if not dt:
        return str(ts) if ts else ""
    return dt.strftime("%I:%M %p")

def format_date(ts):
    dt = parse_dt(ts)
    if not dt:
        return ""
    return dt.strftime("%b %d, %Y")

def format_datetime(ts):
    dt = parse_dt(ts)
    if not dt:
        return str(ts) if ts else ""
    return dt.strftime("%b %d, %Y, %I:%M %p")

def get_user_by_id(user_id):
    if not user_id:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_email(email):
    if not email:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_all_users(exclude_user_id=None, query=None):
    conn = get_db()
    sql = "SELECT id, name, email, is_online, created_at FROM users WHERE 1=1"
    params = []
    if exclude_user_id:
        sql += " AND id != ?"
        params.append(exclude_user_id)
    if query:
        sql += " AND (LOWER(name) LIKE ? OR LOWER(email) LIKE ?)"
        q_like = f"%{query.lower()}%"
        params.extend([q_like, q_like])
    sql += " ORDER BY name ASC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_user(name, email, password_hash):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, is_online, created_at)
        VALUES (?, LOWER(?), ?, 1, CURRENT_TIMESTAMP)
    """, (name.strip(), email.strip(), password_hash))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)

def set_user_online(user_id, is_online):
    conn = get_db()
    conn.execute("UPDATE users SET is_online = ? WHERE id = ?", (1 if is_online else 0, user_id))
    conn.commit()
    conn.close()

def get_user_conversations(user_id):
    conn = get_db()
    query = """
        SELECT c.id, c.is_group, c.name, c.created_at, cm.last_read_time
        FROM conversations c
        JOIN conversation_members cm ON c.id = cm.conversation_id
        LEFT JOIN messages m ON c.id = m.conversation_id
        WHERE cm.user_id = ?
        GROUP BY c.id
        ORDER BY COALESCE(MAX(m.created_at), c.created_at) DESC
    """
    conv_rows = conn.execute(query, (user_id,)).fetchall()

    result = []
    for c in conv_rows:
        conv_id = c['id']
        is_group = bool(c['is_group'])

        if is_group:
            display_name = c['name'] or 'Group Chat'
            target_email = ''
            is_online = False
        else:
            other_member = conn.execute("""
                SELECT u.name, u.email, u.is_online
                FROM conversation_members cm
                JOIN users u ON cm.user_id = u.id
                WHERE cm.conversation_id = ? AND cm.user_id != ?
            """, (conv_id, user_id)).fetchone()

            if other_member:
                display_name = other_member['name']
                target_email = other_member['email']
                is_online = bool(other_member['is_online'])
            else:
                display_name = 'Direct Chat'
                target_email = ''
                is_online = False

        last_msg = conn.execute("""
            SELECT text, file_url, file_name, is_deleted, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC LIMIT 1
        """, (conv_id,)).fetchone()

        last_text = ''
        last_time = ''
        if last_msg:
            if last_msg['is_deleted']:
                last_text = 'This message was deleted'
            elif last_msg['file_url']:
                is_img = any((last_msg['file_name'] or '').lower().endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'))
                last_text = '📷 Photo' if is_img else f"📎 {last_msg['file_name'] or 'Attachment'}"
            else:
                last_text = last_msg['text'] or ''
            last_time = format_timestamp(last_msg['created_at'])

        unread_sql = """
            SELECT COUNT(*) AS count
            FROM messages
            WHERE conversation_id = ? AND sender_id != ?
        """
        params = [conv_id, user_id]
        if c['last_read_time']:
            unread_sql += " AND created_at > ?"
            params.append(c['last_read_time'])
        
        unread_row = conn.execute(unread_sql, params).fetchone()
        unread_count = unread_row['count'] if unread_row else 0

        result.append({
            'id': str(conv_id),
            'is_group': is_group,
            'name': display_name,
            'email': target_email,
            'is_online': is_online,
            'last_message': last_text,
            'last_time': last_time,
            'unread_count': unread_count
        })

    conn.close()
    return result

def get_or_create_direct_conversation(user_id, target_user_id):
    conn = get_db()
    cursor = conn.cursor()

    existing_query = """
        SELECT c.id FROM conversations c
        JOIN conversation_members cm1 ON c.id = cm1.conversation_id AND cm1.user_id = ?
        JOIN conversation_members cm2 ON c.id = cm2.conversation_id AND cm2.user_id = ?
        WHERE c.is_group = 0 LIMIT 1
    """
    existing = cursor.execute(existing_query, (user_id, target_user_id)).fetchone()

    target_user = cursor.execute("SELECT name, email, is_online FROM users WHERE id = ?", (target_user_id,)).fetchone()
    if not target_user:
        conn.close()
        return None

    if existing:
        conv_id = existing['id']
        conn.close()
        return {
            'id': str(conv_id),
            'name': target_user['name'],
            'email': target_user['email'],
            'is_online': bool(target_user['is_online'])
        }

    cursor.execute("INSERT INTO conversations (is_group, name, created_at) VALUES (0, NULL, CURRENT_TIMESTAMP)")
    conv_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO conversation_members (conversation_id, user_id, is_admin, last_read_time)
        VALUES (?, ?, 1, CURRENT_TIMESTAMP), (?, ?, 0, CURRENT_TIMESTAMP)
    """, (conv_id, user_id, conv_id, target_user_id))

    conn.commit()
    conn.close()
    return {
        'id': str(conv_id),
        'name': target_user['name'],
        'email': target_user['email'],
        'is_online': bool(target_user['is_online'])
    }

def create_group_conversation(creator_id, name, member_ids):
    conn = get_db()
    cursor = conn.cursor()

    creator = cursor.execute("SELECT name FROM users WHERE id = ?", (creator_id,)).fetchone()
    creator_name = creator['name'] if creator else 'User'

    cursor.execute("INSERT INTO conversations (is_group, name, created_at) VALUES (1, ?, CURRENT_TIMESTAMP)", (name.strip(),))
    conv_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO conversation_members (conversation_id, user_id, is_admin, last_read_time)
        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
    """, (conv_id, creator_id))

    for uid in member_ids:
        if uid != creator_id:
            cursor.execute("""
                INSERT OR IGNORE INTO conversation_members (conversation_id, user_id, is_admin, last_read_time)
                VALUES (?, ?, 0, CURRENT_TIMESTAMP)
            """, (conv_id, uid))

    cursor.execute("""
        INSERT INTO messages (conversation_id, sender_id, sender_name, text, is_edited, is_deleted, created_at)
        VALUES (?, ?, ?, ?, 0, 0, CURRENT_TIMESTAMP)
    """, (conv_id, creator_id, creator_name, f"Group '{name.strip()}' was created."))

    conn.commit()
    conn.close()
    return {'id': str(conv_id), 'name': name.strip()}

def get_conversation_details(conv_id, current_user_id):
    conn = get_db()
    conv = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    if not conv:
        conn.close()
        return None

    members_rows = conn.execute("""
        SELECT cm.user_id, cm.is_admin, u.name, u.email, u.is_online
        FROM conversation_members cm
        JOIN users u ON cm.user_id = u.id
        WHERE cm.conversation_id = ?
    """, (conv_id,)).fetchall()

    is_admin = False
    other_email = ''
    other_name = ''
    members_data = []

    for m in members_rows:
        members_data.append({
            'user_id': m['user_id'],
            'name': m['name'],
            'email': m['email'],
            'is_admin': bool(m['is_admin']),
            'is_online': bool(m['is_online'])
        })
        if m['user_id'] == current_user_id and m['is_admin']:
            is_admin = True
        if not conv['is_group'] and m['user_id'] != current_user_id:
            other_email = m['email']
            other_name = m['name']

    conn.close()
    return {
        'id': str(conv['id']),
        'is_group': bool(conv['is_group']),
        'name': conv['name'],
        'is_admin': is_admin,
        'other_email': other_email,
        'other_name': other_name,
        'members': members_data
    }

def mark_conversation_read(conv_id, user_id):
    conn = get_db()
    conn.execute("""
        UPDATE conversation_members
        SET last_read_time = CURRENT_TIMESTAMP
        WHERE conversation_id = ? AND user_id = ?
    """, (conv_id, user_id))
    conn.execute("""
        UPDATE messages
        SET status = 'seen'
        WHERE conversation_id = ? AND sender_id != ?
    """, (conv_id, user_id))
    conn.commit()
    conn.close()

def mark_messages_delivered(user_id):
    conn = get_db()
    conn.execute("""
        UPDATE messages
        SET status = 'delivered'
        WHERE status = 'sent' AND sender_id != ? AND conversation_id IN (
            SELECT conversation_id FROM conversation_members WHERE user_id = ?
        )
    """, (user_id, user_id))
    conn.commit()
    conn.close()

def add_group_member(conv_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO conversation_members (conversation_id, user_id, is_admin, last_read_time)
        VALUES (?, ?, 0, CURRENT_TIMESTAMP)
    """, (conv_id, user_id))
    conn.commit()
    conn.close()

def remove_group_member(conv_id, user_id):
    conn = get_db()
    conn.execute("DELETE FROM conversation_members WHERE conversation_id = ? AND user_id = ?", (conv_id, user_id))
    conn.commit()
    conn.close()

def clear_conversation_messages(conv_id):
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    conn.commit()
    conn.close()

def get_conversation_messages(conv_id, search_query=None):
    conn = get_db()
    sql = "SELECT * FROM messages WHERE conversation_id = ?"
    params = [conv_id]
    if search_query:
        sql += " AND LOWER(text) LIKE ?"
        params.append(f"%{search_query.lower()}%")
    sql += " ORDER BY id ASC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            'id': str(r['id']),
            'conversation_id': str(r['conversation_id']),
            'sender_id': r['sender_id'],
            'sender_name': r['sender_name'] or 'Unknown',
            'text': 'This message was deleted' if r['is_deleted'] else (r['text'] or ''),
            'file_url': None if r['is_deleted'] else r['file_url'],
            'file_name': None if r['is_deleted'] else r['file_name'],
            'status': r['status'] or 'sent',
            'is_edited': bool(r['is_edited']) and not bool(r['is_deleted']),
            'is_deleted': bool(r['is_deleted']),
            'time': format_timestamp(r['created_at']),
            'date': format_date(r['created_at']),
            'date_time': format_datetime(r['created_at']),
            'created_at': r['created_at']
        })
    return result

def create_message(conv_id, sender_id, sender_name, text, file_url=None, file_name=None):
    conn = get_db()
    cursor = conn.cursor()

    online_recipient = cursor.execute("""
        SELECT 1 FROM conversation_members cm
        JOIN users u ON cm.user_id = u.id
        WHERE cm.conversation_id = ? AND cm.user_id != ? AND u.is_online = 1
        LIMIT 1
    """, (conv_id, sender_id)).fetchone()

    status = 'delivered' if online_recipient else 'sent'

    cursor.execute("""
        INSERT INTO messages (conversation_id, sender_id, sender_name, text, file_url, file_name, status, is_edited, is_deleted, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, CURRENT_TIMESTAMP)
    """, (conv_id, sender_id, sender_name, text, file_url, file_name, status))
    msg_id = cursor.lastrowid
    conn.commit()

    msg = cursor.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()
    conn.close()

    return {
        'id': str(msg['id']),
        'conversation_id': str(msg['conversation_id']),
        'sender_id': msg['sender_id'],
        'sender_name': msg['sender_name'],
        'text': msg['text'] or '',
        'file_url': msg['file_url'],
        'file_name': msg['file_name'],
        'status': msg['status'] or status,
        'is_edited': False,
        'is_deleted': False,
        'time': format_timestamp(msg['created_at']),
        'date': format_date(msg['created_at']),
        'date_time': format_datetime(msg['created_at']),
        'created_at': msg['created_at']
    }

def edit_message(message_id, new_text):
    conn = get_db()
    conn.execute("UPDATE messages SET text = ?, is_edited = 1 WHERE id = ?", (new_text.strip(), message_id))
    conn.commit()
    msg = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    conn.close()
    return dict(msg) if msg else None

def delete_message(message_id):
    conn = get_db()
    conn.execute("UPDATE messages SET is_deleted = 1, text = 'This message was deleted' WHERE id = ?", (message_id,))
    conn.commit()
    msg = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    conn.close()
    return dict(msg) if msg else None
