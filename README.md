# OmniSync — Unified Email & Real-Time Chat Workspace

OmniSync is a modern, high-performance web platform built with **Flask**, **Flask-SocketIO**, **SQLAlchemy**, and a sleek **Glassmorphism / Adaptive UI (Light & Dark mode)**. It is architected for collaborative team development, providing a single unified database and authentication layer serving both **Member 1 (Email Module)** and **Member 2 (Real-Time Chat Module)**.

---

## 👥 Division of Responsibilities

### **Member 2 — Real-Time Chat Module (Fully Implemented)**
All 13 Member 2 tasks from specification:
1. **1-to-1 Messaging**: Start instant direct conversations with any registered teammate.
2. **Group Chat Creation**: Create group channels with custom names, descriptions, and multi-user selection.
3. **Group Member Management**: Group admins can add members, remove members, or leave the group.
4. **Online & Offline Status**: Real-time presence detection powered by Socket.IO (`connect` / `disconnect`) and live status dots.
5. **Typing Indicators**: Smooth 3-dot animated indicator (*"Alice is typing..."*) with debounce timer.
6. **Read Receipts**: Automatically marks messages as read upon viewing; updates ticks to blue double-check in real time.
7. **Message Delivery Status**: 3-tier visual checkmarks:
   - `✓` Single check: Sent & saved to database.
   - `✓✓` Double gray check: Delivered to recipient.
   - `✓✓` Double blue check: Read by recipient.
8. **Message Timestamps**: Human-readable timestamps (*"10:45 AM"*) and automatic day dividers (*"Today"*, *"Yesterday"*).
9. **Edit and Delete Messages**:
   - Edit sent messages with an inline `(edited)` badge indicator.
   - Delete for everyone (*"This message was deleted"* placeholder broadcasted immediately).
10. **Chat File Sharing**:
    - Attach images, PDFs, Word docs, code files, and archives.
    - Drag-and-drop file upload directly into the chat pane.
    - Inline image viewer and downloadable file badge cards with file size calculation.
11. **Chat Search**:
    - Real-time instant search across conversations and users in the sidebar.
    - In-conversation keyword search bar to locate specific messages.
12. **Conversation History**: Full SQLite persistence; chats load complete message logs cleanly.
13. **Chat Notifications**:
    - Real-time unread counter badges on conversation cards.
    - Floating in-app toast alerts when messages arrive from other rooms.
    - Synthesized Web Audio chime notification (zero external audio asset dependencies).

---

### **Member 1 — Email Management Module (Integrated & Ready)**
Shares the same database and user session:
- **Common Authentication**: Login, registration, profile settings, and avatar upload.
- **Mailbox Folders**: Inbox, Sent, Drafts, and Trash.
- **Compose & Send**: Multi-recipient email dispatch with file attachment uploads.
- **Reply & Forward**: Action triggers for rapid communication.
- **Star & Important Markers**: One-click toggles stored in the database.
- **Email Search**: Search by subject, sender, or email body.

---

### **Both Members — Integration**
- **Common Database Schema**: SQLite database with SQLAlchemy ORM (`users`, `conversations`, `conversation_members`, `messages`, `emails`, `email_attachments`).
- **Unified Navigation & Workspace**: Seamless navbar switching between Chat Hub, Mailbox, Admin Dashboard, and Profile.
- **Admin Dashboard**: Live statistics showing total users, active online users, chat volume, email volume, and an audit table.
- **Instant Demo Switcher**: A top quick-switch bar allows instant 1-click switching between test users (`Alice`, `Bob`, `Charlie`, `Diana`, `Admin`) without opening multiple incognito windows.
- **Adaptive Dark / Light Themes**: Stored in `localStorage` with smooth 250ms transitions.

---

## 🚀 Getting Started

### 1. Requirements & Installation
Ensure you have Python 3.10+ installed.

```bash
cd real-time-email-and-chat-system
pip install -r requirements.txt
```

### 2. Seed Demo Accounts & Sample Data
Run the database seeder to initialize the database with pre-configured users, conversations, and sample emails:

```bash
python seed_data.py
```

### 3. Launch the Server
```bash
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Demo Accounts

All test accounts use the password: `password123` (Admin uses `admin123`).

| Username | Email | Role | Module Focus |
|---|---|---|---|
| **alice** | `alice@omnisync.com` | Admin | Member 1 (Email) Lead |
| **bob** | `bob@omnisync.com` | User | Member 2 (Chat) Lead |
| **charlie** | `charlie@omnisync.com` | User | UI / UX Specialist |
| **diana** | `diana@omnisync.com` | User | QA & Automation |
| **admin** | `admin@omnisync.com` | Admin | System Admin Console |

> **Pro-Tip for Testing Live Chat:** Open `http://127.0.0.1:5000` in two side-by-side browser windows (or one regular tab and one incognito tab). Log in as **Alice** on the left and **Bob** on the right. You will immediately see live typing indicators, instant messaging, green presence dots, read receipts, and file sharing in action!
