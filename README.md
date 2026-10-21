# Real-Time Email and Chat System (2-Member Project)

This is a simple Flask and Socket.IO web application built for a 2-member project sharing the same SQLite database.

## Architecture & Responsibilities

- **Same Database (`models.py`)**:
  - `User`: Simple user table (id, name, email, is_online). No passwords or login barriers.
  - `Conversation`: 1-on-1 and Group chats.
  - `ConversationMember`: Members of chats and admins.
  - `Message`: Chat messages with support for file attachments, timestamps, edit/delete.
  - `Email` & `EmailAttachment`: Email messages, folders (inbox, sent, trash), and attachments.

- **Member 2 — Real-Time Chat Module (Fully Implemented)**:
  1. 1-to-1 messaging
  2. Group chat creation
  3. Group member management (add/remove members)
  4. Online / Offline status indicator
  5. Real-time typing indicators ("Alice is typing...")
  6. Read receipts
  7. Message delivery status (tick checkmarks)
  8. Message timestamps (e.g. 10:45 AM)
  9. Edit and Delete messages
  10. File & photo sharing in chat
  11. Chat search
  12. Conversation message history
  13. Chat notifications

- **Member 1 — Email Module (Integrated)**:
  - Inbox, Sent, Trash folders
  - Compose & send emails
  - Starred and Important markers
  - Shared users and database

---

## How to Run

1. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Seed sample data** (creates Alice, Bob, Charlie and test chats):
   ```bash
   python seed.py
   ```

3. **Start the server**:
   ```bash
   python app.py
   ```
   Open **http://127.0.0.1:5000** in your web browser.

---

## How to Test Two Users (Zero Login Complexity)

- In the top navigation bar, there is a **"Current User"** dropdown.
- Simply select **Alice** in one browser tab or window, and select **Bob** in another tab or incognito window.
- You can now chat between Alice and Bob in real-time, see typing indicators, see online dots, and share files immediately!
