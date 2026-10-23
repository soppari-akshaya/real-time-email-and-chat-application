# Real-Time Chat System (SQLite & Flask)

A clean, modular Flask and Socket.IO application built with separate **HTML**, **CSS**, **JS**, and **Python** files using **SQLite** (`instance/database.sqlite`) as the shared database.

---

## 📁 Modular Project Structure

```
real-time-email-and-chat-system/
│
├── database.py              # SQLite connection helper & schema creation
├── models.py                # Data access queries (users, conversations, messages)
├── utils.py                 # Active user resolution & session helpers
├── extensions.py            # Shared Socket.IO instance
├── sockets.py               # Socket.IO real-time event handlers
├── app.py                   # Application factory & Blueprint registration
├── seed.py                  # Database seeder for SQLite
│
├── routes/                  # Modular Python route controllers
│   ├── __init__.py
│   ├── auth_routes.py       # Switch-user & quick-login
│   ├── chat_routes.py       # Chat views, conversation APIs, file upload
│   └── user_routes.py       # Registered users directory & search API
│
├── templates/               # HTML Templates
│   ├── base.html            # Main layout, navbar, active user pill & switch menu
│   └── chat.html            # Real-time chat interface & modals
│
├── static/
│   ├── css/                 # CSS Style Sheets
│   │   ├── style.css        # Base design tokens, typography, navbar
│   │   └── chat.css         # Chat bubbles, attachments, typing indicator, toasts
│   │
│   ├── js/                  # JavaScript Logic (No inline scripts)
│   │   └── chat.js          # Real-time WebSocket chat logic & notifications
│   │
│   └── uploads/             # Chat file & image attachments
│
└── instance/
    └── database.sqlite      # SQLite database file
```

---

## 🗄️ SQLite Database Schema

- **`users`**: `id`, `name`, `email`, `password_hash`, `is_online`, `created_at`
- **`conversations`**: `id`, `is_group`, `name`, `created_at`
- **`conversation_members`**: `id`, `conversation_id`, `user_id`, `is_admin`, `last_read_time`
- **`messages`**: `id`, `conversation_id`, `sender_id`, `sender_name`, `text`, `file_url`, `file_name`, `status`, `is_edited`, `is_deleted`, `created_at`

---

## 🚀 How to Run

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Seed SQLite database** (Akshaya, Harika, Himaja & chats):
   ```bash
   python seed.py
   ```

3. **Start the Flask server**:
   ```bash
   python app.py
   ```
   Open **http://127.0.0.1:5000** in your web browser.

---

## ⚡ Real-Time Chat & User Switching

1. **Direct Access**:
   - Navigate to **http://127.0.0.1:5000** to directly enter the chat workspace.
   - You are immediately authenticated with the active registered user.

2. **Switch Users Anytime**:
   - Use the **"Switch User"** dropdown in the top navbar to instantly toggle between **Akshaya**, **Harika**, **Himaja**, and **Nakka kavya**.

3. **Send Messages to Registered Email Users**:
   - In the chat interface, click **"New Chat"**.
   - Search or click **"Message"** on any registered user, or type their registered email directly.
   - Send real-time chat messages with typing indicators, delivery statuses, file attachments, and bottom-right notifications!
