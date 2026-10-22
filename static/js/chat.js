let socket = io();
let activeConversationId = null;
let activeTargetEmail = null;
let typingTimer = null;
let typingUsers = {};
let notificationsEnabled = localStorage.getItem("chat_notif") !== "false";
let unreadCountTotal = 0;

function updateTypingUI() {
    let box = document.getElementById("typingIndicator");
    if (!box) return;

    let names = Object.values(typingUsers).map(u => u.name);
    if (!names || names.length === 0) {
        box.innerHTML = "";
        return;
    }

    let text = "";
    if (names.length === 1) {
        text = names[0] + " is typing...";
    } else if (names.length === 2) {
        text = names[0] + " and " + names[1] + " are typing...";
    } else {
        text = names[0] + ", " + names[1] + " and " + (names.length - 2) + " others are typing...";
    }

    box.innerHTML = `
        <div class="typing-pill">
            <span>${escapeHtml(text)}</span>
            <span class="typing-dots">
                <span></span><span></span><span></span>
            </span>
        </div>
    `;
}

socket.on('connect', function () {
    console.log("Connected to chat server as User " + CURRENT_USER_ID);
});

socket.on('status_change', function (data) {
    let dot = document.getElementById("status_dot_" + data.user_id);
    if (dot) {
        if (data.is_online) {
            dot.classList.add("online");
        } else {
            dot.classList.remove("online");
        }
    }
    loadConversations();
});

let notifiedMsgIds = new Set();

function handleIncomingNotification(data) {
    if (!data) return;
    let senderId = String(data.sender_id || '');
    let myId = String(CURRENT_USER_ID || '');
    if (senderId && myId && senderId === myId) return;

    let msgId = data.message_id ? String(data.message_id) : (data.id ? String(data.id) : null);
    if (msgId) {
        if (notifiedMsgIds.has(msgId)) return;
        notifiedMsgIds.add(msgId);
        if (notifiedMsgIds.size > 200) {
            let firstKey = notifiedMsgIds.values().next().value;
            notifiedMsgIds.delete(firstKey);
        }
    }

    let senderName = data.sender_name || 'Someone';
    let text = data.text || (data.file_url ? 'Sent an attachment' : 'New message');
    let convId = data.conversation_id;

    triggerChatNotification(senderName, text, convId);
}

socket.on('new_message', function (msg) {
    if (String(activeConversationId) === String(msg.conversation_id)) {
        appendMessage(msg);
        scrollToBottom();
        if (String(msg.sender_id) !== String(CURRENT_USER_ID)) {
            socket.emit('mark_read', { conversation_id: activeConversationId });
        }
    }
    handleIncomingNotification(msg);
    loadConversations();
});

socket.on('message_notification', function (data) {
    handleIncomingNotification(data);
    loadConversations();
});

socket.on('chat_history_cleared', function (data) {
    if (activeConversationId === data.conversation_id) {
        let area = document.getElementById("messagesArea");
        if (area) {
            area.innerHTML = `
                <div class="text-center text-muted my-auto p-4">
                    <i class="bi bi-chat-heart fs-1 text-primary opacity-50 mb-2"></i>
                    <p class="mb-0 fw-semibold text-dark">Chat history cleared.</p>
                    <small class="text-muted">Type below to start a new conversation!</small>
                </div>
            `;
        }
    }
    loadConversations();
});

socket.on('user_typing', function (data) {
    if (activeConversationId === data.conversation_id && data.user_id !== CURRENT_USER_ID) {
        if (typingUsers[data.user_id] && typingUsers[data.user_id].timer) {
            clearTimeout(typingUsers[data.user_id].timer);
        }
        let timer = setTimeout(function () {
            delete typingUsers[data.user_id];
            updateTypingUI();
        }, 3000);
        typingUsers[data.user_id] = { name: data.username, timer: timer };
        updateTypingUI();
    }
});

socket.on('user_stop_typing', function (data) {
    if (activeConversationId === data.conversation_id) {
        if (data.user_id) {
            if (typingUsers[data.user_id] && typingUsers[data.user_id].timer) {
                clearTimeout(typingUsers[data.user_id].timer);
            }
            delete typingUsers[data.user_id];
        } else {
            Object.values(typingUsers).forEach(u => clearTimeout(u.timer));
            typingUsers = {};
        }
        updateTypingUI();
    }
});

socket.on('read_receipt', function (data) {
    if (activeConversationId === data.conversation_id) {
        let wraps = document.querySelectorAll(".msg-status-wrap");
        wraps.forEach(wrap => {
            wrap.className = "msg-status-wrap status-seen";
            let tick = wrap.querySelector(".tick-icon");
            if (tick) {
                tick.className = "bi bi-check2-all tick-icon tick-seen";
            }
            let label = wrap.querySelector(".status-label");
            if (label) {
                label.innerText = "Seen";
            }
        });
    }
});

socket.on('messages_delivered', function () {
    let wraps = document.querySelectorAll(".msg-status-wrap.status-sent");
    wraps.forEach(wrap => {
        wrap.className = "msg-status-wrap status-delivered";
        let tick = wrap.querySelector(".tick-icon");
        if (tick) {
            tick.className = "bi bi-check2-all tick-icon tick-delivered";
        }
        let label = wrap.querySelector(".status-label");
        if (label) {
            label.innerText = "Delivered \u2022 Unseen";
        }
    });
});

socket.on('message_edited', function (data) {
    if (activeConversationId === data.conversation_id) {
        let textSpan = document.getElementById("msg_text_" + data.id);
        if (textSpan) {
            textSpan.innerHTML = escapeHtml(data.text) + ' <small class="text-muted">(edited)</small>';
        }
    }
});

socket.on('message_deleted', function (data) {
    if (activeConversationId === data.conversation_id) {
        let bubble = document.getElementById("msg_bubble_" + data.id);
        if (bubble) {
            bubble.innerHTML = '<em class="text-muted">This message was deleted</em>';
        }
    }
});

function loadConversations() {
    fetch('/api/conversations')
        .then(res => res.json())
        .then(conversations => {
            let container = document.getElementById("conversationList");
            if (!container) return;
            container.innerHTML = "";

            if (!conversations || conversations.length === 0) {
                container.innerHTML = `
                    <div class="text-muted text-center p-4 small">
                        <i class="bi bi-chat-square-dots d-block fs-3 mb-2 opacity-50"></i>
                        No chats yet.<br>Click <strong>"New Chat"</strong> above to message registered users.
                    </div>
                `;
                return;
            }

            conversations.forEach(c => {
                let item = document.createElement("div");
                item.className = "chat-item " + (activeConversationId === c.id ? "active" : "");
                item.onclick = function () { selectConversation(c.id, c.name, c.is_group, c.is_online, c.email); };

                let onlineDot = !c.is_group ? `<span id="status_dot_${c.id}" class="status-dot ${c.is_online ? 'online' : ''} me-2"></span>` : '';
                let badge = c.unread_count > 0 ? `<span class="badge bg-primary rounded-pill ms-1">${c.unread_count}</span>` : '';
                let emailHint = (!c.is_group && c.email) ? `<small class="text-muted d-block text-truncate" style="font-size: 0.75rem; max-width: 170px;">${escapeHtml(c.email)}</small>` : '';

                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <div class="d-flex align-items-center">
                            ${onlineDot}
                            <strong class="text-truncate" style="max-width: 140px;">${escapeHtml(c.name)}</strong>
                        </div>
                        <small class="text-muted" style="font-size: 0.72rem;">${c.last_time || ''}</small>
                    </div>
                    ${emailHint}
                    <div class="d-flex justify-content-between align-items-center mt-1">
                        <small class="text-muted text-truncate" style="max-width: 170px;">${escapeHtml(c.last_message || 'Start messaging...')}</small>
                        ${badge}
                    </div>
                `;
                container.appendChild(item);
            });
        })
        .catch(err => console.error("Error loading conversations:", err));
}

function selectConversation(convId, name, isGroup, isOnline, email = '') {
    if (activeConversationId) {
        socket.emit('leave_room', { conversation_id: activeConversationId });
    }

    activeConversationId = convId;
    activeTargetEmail = email || '';

    Object.values(typingUsers).forEach(u => {
        if (u.timer) clearTimeout(u.timer);
    });
    typingUsers = {};
    updateTypingUI();
    lastRenderedDate = null;

    document.getElementById("chatTitle").innerText = name;
    document.getElementById("chatStatus").innerText = isGroup ? "Group Chat" : (isOnline ? "Online" : "Offline");

    let avatarEl = document.getElementById("chatAvatar");
    if (avatarEl) {
        avatarEl.innerText = (name || '?')[0].toUpperCase();
        avatarEl.classList.remove("d-none");
    }

    let emailBadge = document.getElementById("chatEmailBadge");

    if (!isGroup && email) {
        if (emailBadge) {
            emailBadge.innerText = email;
            emailBadge.classList.remove("d-none");
        }
    } else {
        if (emailBadge) emailBadge.classList.add("d-none");
    }

    let groupBtn = document.getElementById("groupInfoBtn");
    if (groupBtn) {
        if (isGroup) {
            groupBtn.classList.remove("d-none");
        } else {
            groupBtn.classList.add("d-none");
        }
    }

    let searchChatBtn = document.getElementById("searchChatBtn");
    if (searchChatBtn) {
        searchChatBtn.classList.remove("d-none");
    }
    let historyMenu = document.getElementById("chatHistoryMenu");
    if (historyMenu) {
        historyMenu.classList.remove("d-none");
    }
    closeChatSearch();

    document.getElementById("messageInput").disabled = false;
    document.getElementById("sendBtn").disabled = false;
    document.getElementById("messageInput").focus();

    socket.emit('join_room', { conversation_id: convId });
    socket.emit('mark_read', { conversation_id: convId });

    fetch('/api/conversations/' + convId + '/messages')
        .then(res => res.json())
        .then(data => {
            renderMessages(data.messages);
            setupGroupModal(data);
            if (!isGroup && data.other_email) {
                activeTargetEmail = data.other_email;
                if (emailBadge) {
                    emailBadge.innerText = data.other_email;
                    emailBadge.classList.remove("d-none");
                }
            }
            loadConversations();
        });
}

let lastRenderedDate = null;

function renderMessages(messages) {
    let area = document.getElementById("messagesArea");
    area.innerHTML = "";
    lastRenderedDate = null;

    if (!messages || messages.length === 0) {
        area.innerHTML = `
            <div class="text-center text-muted my-auto p-4">
                <i class="bi bi-chat-heart fs-1 text-primary opacity-50 mb-2"></i>
                <p class="mb-0 fw-semibold text-dark">No messages yet.</p>
                <small class="text-muted">Type below to start your conversation!</small>
            </div>
        `;
        return;
    }

    messages.forEach(msg => {
        if (msg.date && msg.date !== lastRenderedDate) {
            let sep = document.createElement("div");
            sep.className = "chat-date-separator";
            sep.innerHTML = `<span><i class="bi bi-calendar3 me-1"></i>${escapeHtml(msg.date)}</span>`;
            area.appendChild(sep);
            lastRenderedDate = msg.date;
        }
        appendMessage(msg, false);
    });
    scrollToBottom();
}

function getStatusMetaHtml(status) {
    if (status === 'seen') {
        return `
            <span class="msg-status-wrap status-seen">
                <i class="bi bi-check2-all tick-icon tick-seen"></i>
                <span class="status-label">Seen</span>
            </span>
        `;
    }
    if (status === 'delivered') {
        return `
            <span class="msg-status-wrap status-delivered">
                <i class="bi bi-check2-all tick-icon tick-delivered"></i>
                <span class="status-label">Delivered &bull; Unseen</span>
            </span>
        `;
    }
    return `
        <span class="msg-status-wrap status-sent">
            <i class="bi bi-check tick-icon tick-sent"></i>
            <span class="status-label">Sent &bull; Unseen</span>
        </span>
    `;
}

function openPhotoPreview(url, title) {
    let img = document.getElementById("photoPreviewImg");
    let t = document.getElementById("photoPreviewTitle");
    if (img) img.src = url;
    if (t) t.innerText = title || "Photo Preview";
    let modalEl = document.getElementById("photoPreviewModal");
    if (modalEl) {
        let modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

function getFileIcon(filename) {
    let ext = (filename || '').split('.').pop().toLowerCase();
    if (['pdf'].includes(ext)) return 'bi-file-earmark-pdf-fill text-danger';
    if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return 'bi-file-earmark-zip-fill text-warning';
    if (['doc', 'docx'].includes(ext)) return 'bi-file-earmark-word-fill text-primary';
    if (['xls', 'xlsx', 'csv'].includes(ext)) return 'bi-file-earmark-excel-fill text-success';
    if (['ppt', 'pptx'].includes(ext)) return 'bi-file-earmark-slides-fill text-danger';
    if (['mp3', 'wav', 'ogg'].includes(ext)) return 'bi-file-earmark-music-fill text-info';
    if (['mp4', 'mov', 'avi', 'mkv'].includes(ext)) return 'bi-file-earmark-play-fill text-danger';
    if (['txt', 'md', 'py', 'js', 'html', 'css', 'json'].includes(ext)) return 'bi-file-earmark-code-fill text-secondary';
    return 'bi-file-earmark-arrow-down-fill text-primary';
}

function appendMessage(msg, checkDate = true) {
    let area = document.getElementById("messagesArea");
    let isMe = (msg.sender_id === CURRENT_USER_ID);

    if (checkDate && msg.date && msg.date !== lastRenderedDate) {
        let sep = document.createElement("div");
        sep.className = "chat-date-separator";
        sep.innerHTML = `<span><i class="bi bi-calendar3 me-1"></i>${escapeHtml(msg.date)}</span>`;
        area.appendChild(sep);
        lastRenderedDate = msg.date;
    }

    let row = document.createElement("div");
    row.className = "message-row " + (isMe ? "me" : "other");
    row.id = "msg_row_" + msg.id;

    let attachmentHtml = '';
    if (msg.file_url) {
        let isImg = /\.(jpg|jpeg|png|gif|webp)$/i.test(msg.file_name || msg.file_url || '');
        if (isImg) {
            attachmentHtml = `
                <div class="chat-photo-card" onclick="openPhotoPreview('${msg.file_url}', '${escapeHtml(msg.file_name || 'Photo')}')" title="Click to view full photo">
                    <img src="${msg.file_url}" class="chat-photo-img" alt="Uploaded photo">
                    <span class="chat-photo-overlay"><i class="bi bi-arrows-fullscreen"></i></span>
                </div>
            `;
        } else {
            let iconClass = getFileIcon(msg.file_name);
            attachmentHtml = `
                <a href="${msg.file_url}" download="${escapeHtml(msg.file_name || 'download')}" class="chat-file-card" target="_blank" title="Download ${escapeHtml(msg.file_name)}">
                    <div class="chat-file-icon"><i class="bi ${iconClass}"></i></div>
                    <div class="chat-file-info">
                        <div class="chat-file-name">${escapeHtml(msg.file_name || 'Attachment')}</div>
                        <div class="chat-file-action"><i class="bi bi-download"></i> Click to download</div>
                    </div>
                </a>
            `;
        }
    }

    let actionButtons = '';
    if (isMe && !msg.is_deleted) {
        actionButtons = `
            <div class="dropdown d-inline-block ms-1">
                <button class="btn btn-sm btn-link text-muted p-0" data-bs-toggle="dropdown" style="font-size: 0.75rem;"><i class="bi bi-three-dots"></i></button>
                <ul class="dropdown-menu dropdown-menu-end shadow-sm">
                    <li><a class="dropdown-item small" href="#" onclick="editMessagePrompt('${msg.id}', '${escapeHtml(msg.text)}'); return false;">Edit</a></li>
                    <li><a class="dropdown-item small text-danger" href="#" onclick="deleteMessage('${msg.id}'); return false;">Delete for everyone</a></li>
                </ul>
            </div>
        `;
    }

    let statusHtml = isMe ? getStatusMetaHtml(msg.status || 'sent') : '';

    let textHtml = '';
    if (msg.text && (!msg.file_url || msg.text !== msg.file_name)) {
        textHtml = `<span id="msg_text_${msg.id}">${escapeHtml(msg.text)}</span>`;
    }

    let timeDisplay = escapeHtml(msg.time || '');

    row.innerHTML = `
        ${!isMe ? `<small class="fw-semibold text-primary mb-1">${escapeHtml(msg.sender_name)}</small>` : ''}
        <div class="message-bubble" id="msg_bubble_${msg.id}">
            ${attachmentHtml}
            ${textHtml}
            ${msg.is_edited ? '<small class="text-muted ms-1" style="font-size: 0.72rem;">(edited)</small>' : ''}
        </div>
        <div class="message-meta">
            <span class="msg-time" title="${escapeHtml(msg.date_time || msg.time || '')}">${timeDisplay}</span>
            ${statusHtml}
            ${actionButtons}
        </div>
    `;

    area.appendChild(row);
}

document.getElementById("chatForm").addEventListener("submit", function (e) {
    e.preventDefault();
    let input = document.getElementById("messageInput");
    let text = input.value.trim();

    if (!text || !activeConversationId) return;

    socket.emit('send_message', {
        conversation_id: activeConversationId,
        text: text
    });

    socket.emit('stop_typing', { conversation_id: activeConversationId });
    input.value = "";
});

document.getElementById("messageInput").addEventListener("input", function () {
    if (!activeConversationId) return;

    socket.emit('typing', { conversation_id: activeConversationId });

    clearTimeout(typingTimer);
    typingTimer = setTimeout(function () {
        socket.emit('stop_typing', { conversation_id: activeConversationId });
    }, 1800);
});

function editMessagePrompt(msgId, currentText) {
    let newText = prompt("Edit your message:", currentText);
    if (newText && newText.trim() !== "") {
        socket.emit('edit_message', {
            message_id: msgId,
            text: newText.trim()
        });
    }
}

function deleteMessage(msgId) {
    if (confirm("Are you sure you want to delete this message for everyone?")) {
        socket.emit('delete_message', { message_id: msgId });
    }
}

function uploadAttachment(inputEl) {
    let file = inputEl.files[0];
    if (!file || !activeConversationId) return;

    let msgInput = document.getElementById("messageInput");
    let caption = msgInput ? msgInput.value.trim() : "";

    let formData = new FormData();
    formData.append("file", file);
    if (caption) {
        formData.append("text", caption);
    }

    fetch('/api/conversations/' + activeConversationId + '/upload', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(() => {
        inputEl.value = "";
        if (msgInput) msgInput.value = "";
    })
    .catch(err => {
        console.error("Upload error:", err);
        inputEl.value = "";
    });
}

let photoInput = document.getElementById("chatPhotoInput");
if (photoInput) {
    photoInput.addEventListener("change", function () {
        uploadAttachment(this);
    });
}

let fileInput = document.getElementById("chatFileInput");
if (fileInput) {
    fileInput.addEventListener("change", function () {
        uploadAttachment(this);
    });
}

function startDirectChat(userId, name, email) {
    fetch('/api/conversations/direct/' + userId, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            let modalEl = document.getElementById('newDirectModal');
            let modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) modalInstance.hide();
            loadConversations();
            selectConversation(data.id, data.name || name || "Direct Chat", false, data.is_online || false, data.email || email || "");
        })
        .catch(err => console.error("Error starting direct chat:", err));
}

function startDirectChatByEmail() {
    let emailInput = document.getElementById("directChatEmailInput");
    let errorBox = document.getElementById("emailChatError");
    let email = emailInput.value.trim().toLowerCase();

    errorBox.classList.add("d-none");
    errorBox.innerText = "";

    if (!email) {
        errorBox.innerText = "Please enter a valid email address.";
        errorBox.classList.remove("d-none");
        return;
    }

    fetch('/api/conversations/direct-by-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(data => { throw new Error(data.error || 'User not found'); });
        }
        return res.json();
    })
    .then(data => {
        let modalEl = document.getElementById('newDirectModal');
        let modalInstance = bootstrap.Modal.getInstance(modalEl);
        if (modalInstance) modalInstance.hide();
        emailInput.value = "";
        loadConversations();
        selectConversation(data.id, data.name, false, data.is_online, data.email);
    })
    .catch(err => {
        errorBox.innerText = err.message;
        errorBox.classList.remove("d-none");
    });
}

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
        let modalInstance = bootstrap.Modal.getInstance(modalEl);
        if (modalInstance) modalInstance.hide();
        document.getElementById("groupNameInput").value = "";
        loadConversations();
        selectConversation(data.id, data.name, true, false);
    });
}

function setupGroupModal(data) {
    let list = document.getElementById("groupMembersList");
    if (!list) return;
    list.innerHTML = "";

    let addSection = document.getElementById("addMemberSection");
    if (addSection) {
        if (data.is_admin) {
            addSection.classList.remove("d-none");
        } else {
            addSection.classList.add("d-none");
        }
    }

    if (data.members) {
        data.members.forEach(m => {
            let li = document.createElement("li");
            li.className = "list-group-item d-flex justify-content-between align-items-center py-2";
            li.innerHTML = `
                <div>
                    <strong>${escapeHtml(m.name)}</strong>
                    ${m.email ? `<small class="text-muted d-block">&lt;${escapeHtml(m.email)}&gt;</small>` : ''}
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

let searchInput = document.getElementById("searchInput");
if (searchInput) {
    searchInput.addEventListener("input", function (e) {
        let q = e.target.value.toLowerCase();
        let items = document.querySelectorAll(".chat-item");
        items.forEach(it => {
            it.style.display = it.innerText.toLowerCase().includes(q) ? "block" : "none";
        });
    });
}

let regFilter = document.getElementById("registeredUserFilter");
if (regFilter) {
    regFilter.addEventListener("input", function (e) {
        let q = e.target.value.toLowerCase().trim();
        let rows = document.querySelectorAll(".registered-user-row");
        rows.forEach(r => {
            let name = r.getAttribute("data-name") || "";
            let email = r.getAttribute("data-email") || "";
            if (!q || name.includes(q) || email.includes(q)) {
                r.style.setProperty("display", "flex", "important");
            } else {
                r.style.setProperty("display", "none", "important");
            }
        });
    });
}

function scrollToBottom() {
    let area = document.getElementById("messagesArea");
    if (area) {
        area.scrollTop = area.scrollHeight;
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function toggleChatSearch() {
    let bar = document.getElementById("chatSearchBar");
    if (!bar) return;
    if (bar.classList.contains("d-none")) {
        bar.classList.remove("d-none");
        let input = document.getElementById("chatSearchInput");
        if (input) {
            input.value = "";
            input.focus();
        }
    } else {
        closeChatSearch();
    }
}

function closeChatSearch() {
    let bar = document.getElementById("chatSearchBar");
    if (bar) bar.classList.add("d-none");
    let input = document.getElementById("chatSearchInput");
    if (input) input.value = "";
    let count = document.getElementById("chatSearchCount");
    if (count) count.innerText = "";
    clearSearchHighlights();
}

function clearSearchHighlights() {
    let marks = document.querySelectorAll(".chat-search-highlight");
    marks.forEach(m => {
        let parent = m.parentNode;
        if (parent) {
            parent.replaceChild(document.createTextNode(m.innerText), m);
            parent.normalize();
        }
    });
    let rows = document.querySelectorAll(".message-row");
    rows.forEach(r => r.style.opacity = "1");
}

function highlightInElement(element, query) {
    let walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
    let textNodes = [];
    let node;
    while (node = walker.nextNode()) {
        if (node.nodeValue.toLowerCase().includes(query)) {
            textNodes.push(node);
        }
    }
    textNodes.forEach(textNode => {
        let text = textNode.nodeValue;
        let idx = text.toLowerCase().indexOf(query);
        if (idx !== -1) {
            let before = text.substring(0, idx);
            let match = text.substring(idx, idx + query.length);
            let after = text.substring(idx + query.length);

            let mark = document.createElement("mark");
            mark.className = "chat-search-highlight";
            mark.textContent = match;

            let frag = document.createDocumentFragment();
            if (before) frag.appendChild(document.createTextNode(before));
            frag.appendChild(mark);
            if (after) frag.appendChild(document.createTextNode(after));

            if (textNode.parentNode) {
                textNode.parentNode.replaceChild(frag, textNode);
            }
        }
    });
}

let chatSearchInput = document.getElementById("chatSearchInput");
if (chatSearchInput) {
    chatSearchInput.addEventListener("input", function (e) {
        let term = e.target.value.trim().toLowerCase();
        clearSearchHighlights();
        let countEl = document.getElementById("chatSearchCount");

        if (!term) {
            if (countEl) countEl.innerText = "";
            return;
        }

        let rows = document.querySelectorAll(".message-row");
        let matchCount = 0;
        let firstMatchRow = null;

        rows.forEach(row => {
            let bubble = row.querySelector(".message-bubble");
            if (!bubble) return;
            let text = bubble.innerText.toLowerCase();
            if (text.includes(term)) {
                matchCount++;
                row.style.opacity = "1";
                if (!firstMatchRow) firstMatchRow = row;
                highlightInElement(bubble, term);
            } else {
                row.style.opacity = "0.3";
            }
        });

        if (countEl) {
            countEl.innerText = matchCount > 0 ? `${matchCount} found` : "No matches";
        }

        if (firstMatchRow) {
            firstMatchRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });
}

function toggleNotifications() {
    notificationsEnabled = !notificationsEnabled;
    localStorage.setItem("chat_notif", notificationsEnabled ? "true" : "false");
    updateNotifBtn();
    if (notificationsEnabled) {
        showToastNotification("Team Workspace", "Notifications enabled. New messages will appear here.", null);
        if ("Notification" in window && Notification.permission !== "granted") {
            Notification.requestPermission();
        }
    }
}

function updateNotifBtn() {
    let icon = document.getElementById("notifIcon");
    if (!icon) return;
    if (notificationsEnabled) {
        icon.className = "bi bi-bell-fill text-primary";
    } else {
        icon.className = "bi bi-bell-slash text-muted";
    }
}

function playNotificationSound() {
    if (!notificationsEnabled) return;
    try {
        let ctx = new (window.AudioContext || window.webkitAudioContext)();
        let osc = ctx.createOscillator();
        let gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = "sine";
        osc.frequency.setValueAtTime(587.33, ctx.currentTime);
        osc.frequency.setValueAtTime(880, ctx.currentTime + 0.1);
        gain.gain.setValueAtTime(0.12, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.35);
    } catch (e) {}
}

function triggerChatNotification(senderName, text, convId) {
    unreadCountTotal++;
    document.title = `(${unreadCountTotal}) New Message - Team Workspace`;

    showToastNotification(senderName, text, convId);

    try {
        playNotificationSound();
    } catch (e) {}

    if ("Notification" in window && Notification.permission === "granted") {
        try {
            let notif = new Notification(senderName || "New Message", {
                body: text || "Sent an attachment",
                icon: "/static/favicon.ico"
            });
            notif.onclick = function () {
                window.focus();
                notif.close();
                if (convId) {
                    fetch('/api/conversations/' + convId + '/messages')
                        .then(res => res.json())
                        .then(data => {
                            selectConversation(convId, data.other_name || senderName, data.is_group, false, data.other_email || '');
                        })
                        .catch(() => {
                            selectConversation(convId, senderName, false, false, '');
                        });
                }
            };
        } catch (e) {}
    }
}

function showToastNotification(senderName, text, convId) {
    let container = document.getElementById("chatToastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "chatToastContainer";
        container.className = "toast-container position-fixed bottom-0 end-0 p-3";
        container.style.zIndex = "99999";
        container.style.pointerEvents = "none";
        document.body.appendChild(container);
    }

    let toastEl = document.createElement("div");
    toastEl.className = "toast chat-notif-toast mb-2 show";
    toastEl.setAttribute("role", "alert");
    toastEl.setAttribute("aria-live", "assertive");
    toastEl.setAttribute("aria-atomic", "true");
    toastEl.style.display = "block";
    toastEl.style.opacity = "1";
    toastEl.style.pointerEvents = "auto";

    let initial = (senderName && senderName.trim().length > 0) ? senderName.trim()[0].toUpperCase() : '?';
    let previewText = text || 'New message received';

    toastEl.innerHTML = `
        <div class="d-flex align-items-center p-3">
            <div class="user-avatar-circle me-3 flex-shrink-0" style="width: 40px; height: 40px; font-size: 0.95rem; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #fff; box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);">
                ${escapeHtml(initial)}
            </div>
            <div class="flex-grow-1 overflow-hidden me-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <strong class="text-truncate text-dark fw-bold" style="font-size: 0.88rem; max-width: 170px;">${escapeHtml(senderName || 'Notification')}</strong>
                    <small class="text-muted" style="font-size: 0.68rem;">Just now</small>
                </div>
                <div class="text-truncate text-secondary" style="font-size: 0.82rem;">${escapeHtml(previewText)}</div>
            </div>
            <button type="button" class="btn-close ms-2" aria-label="Close"></button>
        </div>
    `;

    let isDismissed = false;
    function dismissToast() {
        if (isDismissed) return;
        isDismissed = true;
        toastEl.style.opacity = "0";
        toastEl.style.transform = "translateY(16px) scale(0.96)";
        setTimeout(() => {
            if (toastEl.parentNode) {
                toastEl.parentNode.removeChild(toastEl);
            }
        }, 260);
    }

    let timer = setTimeout(dismissToast, 6000);

    let closeBtn = toastEl.querySelector(".btn-close");
    if (closeBtn) {
        closeBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            clearTimeout(timer);
            dismissToast();
        });
    }

    toastEl.addEventListener("click", function () {
        clearTimeout(timer);
        dismissToast();
        if (convId) {
            fetch('/api/conversations/' + convId + '/messages')
                .then(res => res.json())
                .then(data => {
                    selectConversation(convId, data.other_name || senderName, data.is_group, false, data.other_email || '');
                })
                .catch(() => {
                    selectConversation(convId, senderName, false, false, '');
                });
        }
    });

    container.appendChild(toastEl);
}

window.triggerChatNotification = triggerChatNotification;
window.showToastNotification = showToastNotification;

function exportChatHistory() {
    if (!activeConversationId) return;

    fetch('/api/conversations/' + activeConversationId + '/messages')
        .then(res => res.json())
        .then(data => {
            let title = document.getElementById("chatTitle").innerText || "Chat";
            let lines = [
                `========================================`,
                `Chat Transcript: ${title}`,
                `Exported: ${new Date().toLocaleString()}`,
                `========================================\n`
            ];

            let msgs = data.messages || [];
            if (msgs.length === 0) {
                lines.push("No messages in this conversation.");
            } else {
                msgs.forEach(m => {
                    let datePart = m.date ? `[${m.date} ${m.time}]` : `[${m.time}]`;
                    let content = m.text || '';
                    if (m.file_url) {
                        content += (content ? ' ' : '') + `[Attachment: ${m.file_name} -> ${m.file_url}]`;
                    }
                    lines.push(`${datePart} ${m.sender_name}: ${content}`);
                });
            }

            let blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
            let url = URL.createObjectURL(blob);
            let a = document.createElement("a");
            a.href = url;
            a.download = `chat_history_${title.replace(/[^a-zA-Z0-9_-]/g, '_')}_${Date.now()}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
}

function clearChatHistory() {
    if (!activeConversationId) return;
    if (!confirm("Are you sure you want to clear this conversation history? All messages will be permanently deleted.")) {
        return;
    }

    fetch('/api/conversations/' + activeConversationId + '/clear-history', {
        method: 'POST'
    })
    .then(res => res.json())
    .then(() => {
        let area = document.getElementById("messagesArea");
        if (area) {
            area.innerHTML = `
                <div class="text-center text-muted my-auto p-4">
                    <i class="bi bi-chat-heart fs-1 text-primary opacity-50 mb-2"></i>
                    <p class="mb-0 fw-semibold text-dark">Chat history cleared.</p>
                    <small class="text-muted">Type below to start a new conversation!</small>
                </div>
            `;
        }
        loadConversations();
    })
    .catch(err => console.error("Error clearing history:", err));
}

window.addEventListener("focus", function () {
    unreadCountTotal = 0;
    document.title = "Real-Time Chat - Team Workspace";
});

document.addEventListener("DOMContentLoaded", function () {
    updateNotifBtn();
    loadConversations();
});
