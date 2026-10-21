// Simple Real-Time Chat Engine (Member 2)
let socket = io();
let activeConversationId = null;
let typingTimer = null;

// Connect to Socket.IO
socket.on('connect', function () {
    console.log("Connected to chat server as User " + CURRENT_USER_ID);
});

// Update online/offline presence indicator
socket.on('status_change', function (data) {
    let dot = document.getElementById("status_dot_" + data.user_id);
    if (dot) {
        if (data.is_online) {
            dot.classList.add("online");
        } else {
            dot.classList.remove("online");
        }
    }
});

// Receive new real-time message
socket.on('new_message', function (msg) {
    if (activeConversationId === msg.conversation_id) {
        appendMessage(msg);
        scrollToBottom();
        // Mark message as read
        if (msg.sender_id !== CURRENT_USER_ID) {
            socket.emit('mark_read', { conversation_id: activeConversationId });
        }
    }
    loadConversations(); // Refresh last message in sidebar
});

// Listen for notifications from other chats
socket.on('message_notification', function (data) {
    if (activeConversationId !== data.conversation_id && data.sender_id !== CURRENT_USER_ID) {
        // Simple in-app notification / alert
        console.log("New message from " + data.sender_name + ": " + data.text);
    }
});

// Typing indicator from others
socket.on('user_typing', function (data) {
    if (activeConversationId === data.conversation_id) {
        let box = document.getElementById("typingIndicator");
        box.innerText = data.username + " is typing...";
    }
});

socket.on('user_stop_typing', function (data) {
    if (activeConversationId === data.conversation_id) {
        let box = document.getElementById("typingIndicator");
        box.innerText = "";
    }
});

// Read receipt update
socket.on('read_receipt', function (data) {
    if (activeConversationId === data.conversation_id) {
        let ticks = document.querySelectorAll(".msg-tick");
        ticks.forEach(t => t.classList.add("tick-read"));
    }
});

// Edited message
socket.on('message_edited', function (data) {
    if (activeConversationId === data.conversation_id) {
        let textSpan = document.getElementById("msg_text_" + data.id);
        if (textSpan) {
            textSpan.innerHTML = escapeHtml(data.text) + ' <small class="text-muted">(edited)</small>';
        }
    }
});

// Deleted message
socket.on('message_deleted', function (data) {
    if (activeConversationId === data.conversation_id) {
        let bubble = document.getElementById("msg_bubble_" + data.id);
        if (bubble) {
            bubble.innerHTML = '<em class="text-muted">This message was deleted</em>';
        }
    }
});

// Load all user conversations
function loadConversations() {
    fetch('/api/conversations')
        .then(res => res.json())
        .then(conversations => {
            let container = document.getElementById("conversationList");
            container.innerHTML = "";

            if (conversations.length === 0) {
                container.innerHTML = '<div class="text-muted text-center p-4 small">No chats yet. Click "+" above.</div>';
                return;
            }

            conversations.forEach(c => {
                let item = document.createElement("div");
                item.className = "chat-item " + (activeConversationId === c.id ? "active" : "");
                item.onclick = function () { selectConversation(c.id, c.name, c.is_group, c.is_online); };

                let onlineDot = !c.is_group ? `<span id="status_dot_${c.id}" class="status-dot ${c.is_online ? 'online' : ''} me-2"></span>` : '';
                let badge = c.unread_count > 0 ? `<span class="badge bg-primary rounded-pill">${c.unread_count}</span>` : '';

                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <div class="d-flex align-items-center">
                            ${onlineDot}
                            <strong class="text-truncate" style="max-width: 140px;">${escapeHtml(c.name)}</strong>
                        </div>
                        <small class="text-muted">${c.last_time || ''}</small>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted text-truncate" style="max-width: 170px;">${escapeHtml(c.last_message || 'No messages')}</small>
                        ${badge}
                    </div>
                `;
                container.appendChild(item);
            });
        });
}

// Select and open a conversation
function selectConversation(convId, name, isGroup, isOnline) {
    if (activeConversationId) {
        socket.emit('leave_room', { conversation_id: activeConversationId });
    }

    activeConversationId = convId;

    // Update Header
    document.getElementById("chatTitle").innerText = name;
    document.getElementById("chatStatus").innerText = isGroup ? "Group Chat" : (isOnline ? "Online" : "Offline");

    let groupBtn = document.getElementById("groupInfoBtn");
    if (isGroup) {
        groupBtn.classList.remove("d-none");
    } else {
        groupBtn.classList.add("d-none");
    }

    // Enable Inputs
    document.getElementById("messageInput").disabled = false;
    document.getElementById("sendBtn").disabled = false;
    document.getElementById("messageInput").focus();

    // Join Socket Room
    socket.emit('join_room', { conversation_id: convId });
    socket.emit('mark_read', { conversation_id: convId });

    // Fetch conversation message history
    fetch('/api/conversations/' + convId + '/messages')
        .then(res => res.json())
        .then(data => {
            renderMessages(data.messages);
            setupGroupModal(data);
            loadConversations(); // Clear unread badge
        });
}

// Render message history
function renderMessages(messages) {
    let area = document.getElementById("messagesArea");
    area.innerHTML = "";

    if (messages.length === 0) {
        area.innerHTML = '<div class="text-center text-muted my-auto"><p>No messages yet. Say hello!</p></div>';
        return;
    }

    messages.forEach(msg => {
        appendMessage(msg);
    });
    scrollToBottom();
}

// Append a single message bubble
function appendMessage(msg) {
    let area = document.getElementById("messagesArea");
    let isMe = (msg.sender_id === CURRENT_USER_ID);

    let row = document.createElement("div");
    row.className = "message-row " + (isMe ? "me" : "other");
    row.id = "msg_row_" + msg.id;

    // Checkmark tick for delivery / read
    let tick = isMe ? '<span class="msg-tick tick-read ms-1"><i class="bi bi-check2-all"></i></span>' : '';

    // File / Image Attachment HTML
    let attachmentHtml = '';
    if (msg.file_url) {
        let isImg = /\.(jpg|jpeg|png|gif|webp)$/i.test(msg.file_name || '');
        if (isImg) {
            attachmentHtml = `<img src="${msg.file_url}" class="chat-attachment-img d-block" onclick="window.open('${msg.file_url}', '_blank')">`;
        } else {
            attachmentHtml = `<a href="${msg.file_url}" download class="file-link d-inline-block"><i class="bi bi-file-earmark-arrow-down me-1"></i> ${escapeHtml(msg.file_name)}</a>`;
        }
    }

    // Action buttons for message sender (Edit & Delete)
    let actionButtons = '';
    if (isMe && !msg.is_deleted) {
        actionButtons = `
            <div class="dropdown d-inline-block ms-1">
                <button class="btn btn-sm btn-link text-muted p-0" data-bs-toggle="dropdown" style="font-size: 0.75rem;"><i class="bi bi-three-dots"></i></button>
                <ul class="dropdown-menu dropdown-menu-end shadow-sm">
                    <li><a class="dropdown-item small" href="#" onclick="editMessagePrompt(${msg.id}, '${escapeHtml(msg.text)}'); return false;">Edit</a></li>
                    <li><a class="dropdown-item small text-danger" href="#" onclick="deleteMessage(${msg.id}); return false;">Delete for everyone</a></li>
                </ul>
            </div>
        `;
    }

    row.innerHTML = `
        ${!isMe ? `<small class="fw-semibold text-primary mb-1">${escapeHtml(msg.sender_name)}</small>` : ''}
        <div class="message-bubble" id="msg_bubble_${msg.id}">
            ${attachmentHtml}
            <span id="msg_text_${msg.id}">${escapeHtml(msg.text)}</span>
            ${msg.is_edited ? '<small class="text-muted ms-1">(edited)</small>' : ''}
        </div>
        <div class="message-meta">
            <span>${msg.time}</span>
            ${tick}
            ${actionButtons}
        </div>
    `;

    area.appendChild(row);
}

// Send Message Form Submit
document.getElementById("chatForm").addEventListener("submit", function (e) {
    e.preventDefault();
    let input = document.getElementById("messageInput");
    let text = input.value.trim();

    if (!text || !activeConversationId) return;

    // Send via Socket.IO
    socket.emit('send_message', {
        conversation_id: activeConversationId,
        text: text
    });

    socket.emit('stop_typing', { conversation_id: activeConversationId });

    input.value = "";
});

// Typing Handler (fires typing / stop_typing events)
document.getElementById("messageInput").addEventListener("input", function () {
    if (!activeConversationId) return;

    socket.emit('typing', { conversation_id: activeConversationId });

    clearTimeout(typingTimer);
    typingTimer = setTimeout(function () {
        socket.emit('stop_typing', { conversation_id: activeConversationId });
    }, 2000);
});

// Edit Message
function editMessagePrompt(msgId, currentText) {
    let newText = prompt("Edit your message:", currentText);
    if (newText && newText.trim() !== "") {
        socket.emit('edit_message', {
            message_id: msgId,
            text: newText.trim()
        });
    }
}

// Delete Message
function deleteMessage(msgId) {
    if (confirm("Are you sure you want to delete this message for everyone?")) {
        socket.emit('delete_message', { message_id: msgId });
    }
}

// Chat File Upload (Image / Document Sharing)
document.getElementById("chatFileInput").addEventListener("change", function () {
    let file = this.files[0];
    if (!file || !activeConversationId) return;

    let formData = new FormData();
    formData.append("file", file);

    fetch('/api/conversations/' + activeConversationId + '/upload', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(msg => {
        document.getElementById("chatFileInput").value = "";
    });
});

// Start Direct 1-on-1 Chat
function startDirectChat(userId) {
    fetch('/api/conversations/direct/' + userId, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            let modalEl = document.getElementById('newDirectModal');
            bootstrap.Modal.getInstance(modalEl).hide();
            loadConversations();
            selectConversation(data.id, "Chat", false, false);
        });
}

// Create Group Chat
function createGroupChat() {
    let name = document.getElementById("groupNameInput").value.trim();
    if (!name) {
        alert("Please enter a group name");
        return;
    }

    let checkedBoxes = document.querySelectorAll(".group-member-cb:checked");
    let memberIds = Array.from(checkedBoxes).map(cb => parseInt(cb.value));

    fetch('/api/conversations/group', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, member_ids: memberIds })
    })
    .then(res => res.json())
    .then(data => {
        let modalEl = document.getElementById('newGroupModal');
        bootstrap.Modal.getInstance(modalEl).hide();
        document.getElementById("groupNameInput").value = "";
        loadConversations();
        selectConversation(data.id, data.name, true, false);
    });
}

// Group Info Modal Setup
function setupGroupModal(data) {
    let list = document.getElementById("groupMembersList");
    list.innerHTML = "";

    let addSection = document.getElementById("addMemberSection");
    if (data.is_admin) {
        addSection.classList.remove("d-none");
    } else {
        addSection.classList.add("d-none");
    }

    data.members.forEach(m => {
        let li = document.createElement("li");
        li.className = "list-group-item d-flex justify-content-between align-items-center py-2";
        li.innerHTML = `
            <div>
                <strong>${escapeHtml(m.name)}</strong>
                ${m.is_admin ? '<span class="badge bg-secondary ms-1">Admin</span>' : ''}
                <small class="text-muted d-block">${m.is_online ? 'Online' : 'Offline'}</small>
            </div>
            ${data.is_admin && m.user_id !== CURRENT_USER_ID ? `
                <button class="btn btn-sm btn-outline-danger" onclick="removeGroupMember(${m.user_id})">Remove</button>
            ` : ''}
        `;
        list.appendChild(li);
    });
}

function addGroupMember() {
    let select = document.getElementById("addMemberSelect");
    let userId = select.value;
    if (!userId) return;

    fetch('/api/conversations/' + activeConversationId + '/add-member', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: parseInt(userId) })
    })
    .then(res => res.json())
    .then(() => {
        select.value = "";
        bootstrap.Modal.getInstance(document.getElementById('groupInfoModal')).hide();
        selectConversation(activeConversationId, document.getElementById("chatTitle").innerText, true, false);
    });
}

function removeGroupMember(userId) {
    if (!confirm("Remove this user from the group?")) return;

    fetch('/api/conversations/' + activeConversationId + '/remove-member/' + userId, {
        method: 'POST'
    })
    .then(res => res.json())
    .then(() => {
        bootstrap.Modal.getInstance(document.getElementById('groupInfoModal')).hide();
        selectConversation(activeConversationId, document.getElementById("chatTitle").innerText, true, false);
    });
}

// In-chat Search Input
document.getElementById("searchInput").addEventListener("input", function (e) {
    let q = e.target.value.toLowerCase();
    let items = document.querySelectorAll(".chat-item");
    items.forEach(it => {
        it.style.display = it.innerText.toLowerCase().includes(q) ? "block" : "none";
    });
});

function scrollToBottom() {
    let area = document.getElementById("messagesArea");
    area.scrollTop = area.scrollHeight;
}

function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Initial load on page start
document.addEventListener("DOMContentLoaded", function () {
    loadConversations();
});
