# Real-Time Email and Chat System (MongoDB & Flask)

A simple, clean Flask and Socket.IO application built for a 2-member project using **MongoDB** (`chat_email_db`) as the common database.

---

## 🗄️ MongoDB Collections (Shared between both members)

- **`users`**: `{ id: 1, name: "Alice", email: "alice@college.edu", is_online: false }`
- **`conversations`**: Stores both 1-on-1 and Group chats with member lists and roles.
- **`messages`**: Real-time chat messages with timestamps, read receipts, attachments, and edit/delete flags.
- **`emails`**: Member 1 email storage (inbox, sent, trash, subject, body, starred).

---

## 👥 Module Breakdown

### **Member 2 — Real-Time Chat Module (Fully Implemented)**
1. **One-to-one messaging**: Instant direct chat with any user.
2. **Group chat creation**: Create group chats with custom names and multiple members.
3. **Group member management**: Add or remove members in group info.
4. **Online / Offline status**: Live presence status indicator dot (green/gray).
5. **Typing indicators**: Displays *"Alice is typing..."* in real time.
6. **Read receipts**: Messages marked as read when conversation is opened.
7. **Message delivery status**: Double tick checkmarks (`✓✓`) that turn blue when read.
8. **Message timestamps**: Formatted times (e.g. `10:45 AM`) on all message bubbles.
9. **Edit and Delete messages**: Edit sent text with `(edited)` tag or delete for everyone.
10. **Chat file sharing**: Attach images (with preview) or documents (with download link).
11. **Chat search**: Real-time filter across conversations and message history.
12. **Conversation history**: Loaded directly from MongoDB on chat selection.
13. **Chat notifications**: Unread count badges in conversation list.

### **Member 1 — Email Module (Integrated on Same MongoDB)**
- Folders: Inbox, Sent, Trash
- Compose and send emails
- Starred & Important markers
- Common MongoDB collections and users

---

## 🚀 How to Run

1. **Ensure MongoDB is running** on your local machine (`mongodb://localhost:27017`).

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Seed MongoDB with sample data** (Alice, Bob, Charlie & chats):
   ```bash
   python seed.py
   ```

4. **Start the Flask server**:
   ```bash
   python app.py
   ```
   Open **http://127.0.0.1:5000** in your web browser.

---

## ⚡ Testing Two Users (No Login Complexity)

- In the top navigation bar, select **Alice** in one tab or window.
- In another tab or incognito window, select **Bob** from the **"Current User"** dropdown.
- Click on the chat between Alice and Bob to test real-time messaging, typing indicators, online status, and file sharing in action!
