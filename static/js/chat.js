// Member 2: Complete Real-Time Chat Engine
window.currentConversationId = null;
let currentConversation = null;
let typingTimeout = null;
let isTyping = false;
let currentEditingMessageId = null;

const ChatApp = {
  currentUserId: null,

  init(currentUserId) {
    this.currentUserId = currentUserId;
    this.bindEvents();
    this.loadConversations();
    this.setupSocketListeners();
  },

  bindEvents() {
    // Search conversation input
    const convSearchInput = document.getElementById('search-conversations-input');
    if (convSearchInput) {
      convSearchInput.addEventListener('input', (e) => {
        this.filterConversations(e.target.value.toLowerCase());
      });
    }

    // In-chat message search toggle
    const toggleSearchBtn = document.getElementById('toggle-msg-search-btn');
    const searchBar = document.getElementById('in-chat-search-bar');
    const msgSearchInput = document.getElementById('msg-search-input');
    if (toggleSearchBtn && searchBar) {
      toggleSearchBtn.addEventListener('click', () => {
        searchBar.classList.toggle('show');
        if (searchBar.classList.contains('show') && msgSearchInput) {
          msgSearchInput.focus();
        }
      });
    }

    if (msgSearchInput) {
      msgSearchInput.addEventListener('input', (e) => {
        this.filterChatMessages(e.target.value.toLowerCase());
      });
    }

    // Message Input & Typing Handler
    const msgInput = document.getElementById('message-input');
    if (msgInput) {
      msgInput.addEventListener('input', () => {
        this.handleTypingInput();
      });

      msgInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    }

    // Send Button
    const sendBtn = document.getElementById('send-message-btn');
    if (sendBtn) {
      sendBtn.addEventListener('click', () => {
        this.sendMessage();
      });
    }

    // File Attachment Input
    const fileInput = document.getElementById('file-attachment-input');
    if (fileInput) {
      fileInput.addEventListener('change', (e) => {
        this.handleFileSelected(e.target.files[0]);
      });
    }

    // Drag and Drop files onto chat feed
    const messagesArea = document.getElementById('chat-messages-area');
    if (messagesArea) {
      messagesArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        messagesArea.style.border = '2px dashed var(--primary)';
      });
      messagesArea.addEventListener('dragleave', () => {
        messagesArea.style.border = 'none';
      });
      messagesArea.addEventListener('drop', (e) => {
        e.preventDefault();
        messagesArea.style.border = 'none';
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          this.handleFileSelected(e.dataTransfer.files[0]);
        }
      });
    }

    // Create Group Modal Handlers
    const newGroupBtn = document.getElementById('btn-new-group');
    const groupModal = document.getElementById('create-group-modal');
    if (newGroupBtn && groupModal) {
      newGroupBtn.addEventListener('click', () => {
        groupModal.classList.add('show');
      });
    }

    const cancelGroupBtn = document.getElementById('cancel-group-btn');
    if (cancelGroupBtn && groupModal) {
      cancelGroupBtn.addEventListener('click', () => {
        groupModal.classList.remove('show');
      });
    }

    const submitGroupBtn = document.getElementById('submit-create-group-btn');
    if (submitGroupBtn) {
      submitGroupBtn.addEventListener('click', () => {
        this.createGroupChat();
      });
    }

    // Direct Chat Trigger Modal
    const newDirectBtn = document.getElementById('btn-new-direct');
    const directModal = document.getElementById('new-direct-modal');
    if (newDirectBtn && directModal) {
      newDirectBtn.addEventListener('click', () => {
        directModal.classList.add('show');
      });
    }
    const cancelDirectBtn = document.getElementById('cancel-direct-btn');
    if (cancelDirectBtn && directModal) {
      cancelDirectBtn.addEventListener('click', () => {
        directModal.classList.remove('show');
      });
    }

    // Group Details / Management Modal
    const chatHeaderUser = document.getElementById('active-chat-user-click');
    const groupDetailsModal = document.getElementById('group-details-modal');
    if (chatHeaderUser && groupDetailsModal) {
      chatHeaderUser.addEventListener('click', () => {
        if (currentConversation && currentConversation.is_group) {
          this.openGroupDetailsModal();
        }
      });
    }

    const closeGroupDetailsBtn = document.getElementById('close-group-details-btn');
    if (closeGroupDetailsBtn && groupDetailsModal) {
      closeGroupDetailsBtn.addEventListener('click', () => {
        groupDetailsModal.classList.remove('show');
      });
    }

    // Add Member in Group
    const addMemberBtn = document.getElementById('btn-add-group-member');
    if (addMemberBtn) {
      addMemberBtn.addEventListener('click', () => {
        this.addGroupMember();
      });
    }

    // Leave Group
    const leaveGroupBtn = document.getElementById('btn-leave-group');
    if (leaveGroupBtn) {
      leaveGroupBtn.addEventListener('click', () => {
        this.leaveCurrentGroup();
      });
    }
  },

  setupSocketListeners() {
    if (!socket) return;

    // Receive new message
    socket.on('new_message', (msg) => {
      if (window.currentConversationId == msg.conversation_id) {
        this.appendMessage(msg);
        this.scrollToBottom();

        // If not sent by me, emit mark_read
        if (msg.sender_id != this.currentUserId) {
          socket.emit('mark_read', { conversation_id: window.currentConversationId });
        }
      }

      // Update snippet and badge in conversation list
      this.updateConversationCard(msg);
    });

    // Real-time typing indicators
    socket.on('user_typing', (data) => {
      if (window.currentConversationId == data.conversation_id) {
        const bar = document.getElementById('typing-indicator-bar');
        const textSpan = document.getElementById('typing-indicator-text');
        if (bar && textSpan) {
          textSpan.textContent = `${data.username} is typing...`;
          bar.classList.add('show');
        }
      }
    });

    socket.on('user_stop_typing', (data) => {
      if (window.currentConversationId == data.conversation_id) {
        const bar = document.getElementById('typing-indicator-bar');
        if (bar) bar.classList.remove('show');
      }
    });

    // Read Receipts
    socket.on('messages_read', (data) => {
      if (window.currentConversationId == data.conversation_id) {
        // Turn tick marks blue for all messages <= last_read_message_id
        const ticks = document.querySelectorAll('.status-tick');
        ticks.forEach(tick => {
          const msgId = parseInt(tick.dataset.msgId || '0');
          if (msgId <= data.last_read_message_id) {
            tick.className = 'status-tick read';
            tick.innerHTML = '<i class="bi bi-check2-all" title="Read"></i>';
          }
        });
      }
    });

    // Message Edited
    socket.on('message_edited', (msg) => {
      if (window.currentConversationId == msg.conversation_id) {
        const msgTextEl = document.getElementById(`msg-text-${msg.id}`);
        if (msgTextEl) {
          msgTextEl.innerHTML = `${this.escapeHtml(msg.text)} <span class="msg-edited-tag">(edited)</span>`;
        }
      }
    });

    // Message Deleted
    socket.on('message_deleted', (data) => {
      if (window.currentConversationId == data.conversation_id) {
        const bubble = document.getElementById(`msg-bubble-${data.message_id}`);
        if (bubble) {
          bubble.className = 'msg-bubble deleted';
          bubble.innerHTML = `<em>This message was deleted</em>`;
        }
      }
    });
  },

  async loadConversations() {
    try {
      const res = await fetch('/api/conversations');
      const convs = await res.json();
      const listContainer = document.getElementById('conversations-list');
      if (!listContainer) return;

      listContainer.innerHTML = '';

      if (convs.length === 0) {
        listContainer.innerHTML = `
          <div style="text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem;">
            No conversations yet.<br>Click "+" to start chatting!
          </div>
        `;
        return;
      }

      convs.forEach(c => {
        const item = this.renderConversationItem(c);
        listContainer.appendChild(item);
      });

      // Auto-select first conversation or persist selection
      if (!window.currentConversationId && convs.length > 0) {
        this.selectConversation(convs[0].id);
      }
    } catch (err) {
      console.error("Error loading conversations:", err);
    }
  },

  renderConversationItem(conv) {
    const el = document.createElement('div');
    el.className = `conv-item ${window.currentConversationId == conv.id ? 'active' : ''}`;
    el.id = `conv-item-${conv.id}`;
    el.onclick = () => this.selectConversation(conv.id);

    const isOnline = conv.other_user ? conv.other_user.is_online : false;
    const presenceClass = isOnline ? 'online' : 'offline';
    const lastMsgText = conv.last_message ? (conv.last_message.text || 'Attachment') : 'No messages yet';
    const timeText = conv.last_message ? conv.last_message.timestamp_str : '';

    el.innerHTML = `
      <div class="conv-avatar-wrap">
        <img src="${conv.avatar_url}" alt="${conv.name}" class="conv-avatar">
        ${!conv.is_group && conv.other_user ? `<span class="presence-dot ${presenceClass} user-presence-${conv.other_user.id}"></span>` : ''}
      </div>
      <div class="conv-info">
        <div class="conv-top-row">
          <span class="conv-name">${this.escapeHtml(conv.name)}</span>
          <span class="conv-time">${timeText}</span>
        </div>
        <div class="conv-bottom-row">
          <span class="conv-snippet" id="snippet-${conv.id}">${this.escapeHtml(lastMsgText)}</span>
          <span class="unread-badge" id="badge-${conv.id}" style="${conv.unread_count > 0 ? '' : 'display: none;'}">${conv.unread_count}</span>
        </div>
      </div>
    `;
    return el;
  },

  async selectConversation(convId) {
    if (window.currentConversationId && socket) {
      socket.emit('leave_conversation', { conversation_id: window.currentConversationId });
    }

    window.currentConversationId = convId;

    // Highlight active item
    document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
    const activeEl = document.getElementById(`conv-item-${convId}`);
    if (activeEl) activeEl.classList.add('active');

    // Reset unread badge
    const badge = document.getElementById(`badge-${convId}`);
    if (badge) {
      badge.textContent = '0';
      badge.style.display = 'none';
    }

    // Show Chat Main Pane & Hide Empty State
    const emptyState = document.getElementById('chat-empty-state');
    const activePane = document.getElementById('chat-active-pane');
    if (emptyState) emptyState.style.display = 'none';
    if (activePane) activePane.style.display = 'flex';

    // Fetch conversation details & messages
    try {
      const [convRes, msgRes] = await Promise.all([
        fetch(`/api/conversations/${convId}`),
        fetch(`/api/conversations/${convId}/messages`)
      ]);

      currentConversation = await convRes.json();
      const messages = await msgRes.json();

      this.updateChatHeader(currentConversation);
      this.renderMessagesFeed(messages);

      // Join Socket.IO room & emit read receipts
      if (socket) {
        socket.emit('join_conversation', { conversation_id: convId });
      }

      this.scrollToBottom();
    } catch (err) {
      console.error("Error selecting conversation:", err);
    }
  },

  updateChatHeader(conv) {
    const avatarImg = document.getElementById('active-chat-avatar');
    const nameEl = document.getElementById('active-chat-name');
    const statusEl = document.getElementById('active-chat-status');

    if (avatarImg) avatarImg.src = conv.avatar_url;
    if (nameEl) {
      nameEl.innerHTML = `
        ${this.escapeHtml(conv.name)}
        ${conv.is_group ? `<span class="badge" style="font-size: 0.65rem; background: var(--bg-input); color: var(--text-muted); border: 1px solid var(--border-color);">${conv.member_count} members</span>` : ''}
      `;
    }

    if (statusEl) {
      if (conv.is_group) {
        statusEl.className = 'active-chat-status';
        statusEl.innerHTML = 'Click to view group members';
      } else if (conv.other_user) {
        statusEl.dataset.otherUserId = conv.other_user.id;
        if (conv.other_user.is_online) {
          statusEl.className = 'active-chat-status online';
          statusEl.innerHTML = '<i class="bi bi-circle-fill" style="font-size: 8px;"></i> Online';
        } else {
          statusEl.className = 'active-chat-status';
          statusEl.innerHTML = 'Offline';
        }
      }
    }
  },

  renderMessagesFeed(messages) {
    const feed = document.getElementById('chat-messages-area');
    if (!feed) return;

    feed.innerHTML = '';
    let lastDate = null;

    messages.forEach(msg => {
      // Date headers (e.g. Today, Yesterday, Date)
      if (msg.date_str && msg.date_str !== lastDate) {
        lastDate = msg.date_str;
        const divider = document.createElement('div');
        divider.className = 'date-divider';
        divider.innerHTML = `<span>${this.formatDateHeader(msg.date_str)}</span>`;
        feed.appendChild(divider);
      }

      const row = this.createMessageRowElement(msg);
      feed.appendChild(row);
    });
  },

  createMessageRowElement(msg) {
    const isMine = msg.sender_id == this.currentUserId;
    const row = document.createElement('div');
    row.className = `msg-row ${isMine ? 'outgoing' : 'incoming'}`;
    row.id = `msg-row-${msg.id}`;

    // Status Tick icon
    let statusIcon = '<i class="bi bi-check" title="Sent"></i>';
    let tickClass = 'status-tick';
    if (msg.status === 'read') {
      statusIcon = '<i class="bi bi-check2-all" title="Read"></i>';
      tickClass = 'status-tick read';
    } else if (msg.status === 'delivered') {
      statusIcon = '<i class="bi bi-check2" title="Delivered"></i>';
    }

    // Attachment Content
    let attachmentHtml = '';
    if (msg.message_type === 'image' && msg.file_path) {
      attachmentHtml = `<img src="${msg.file_path}" alt="attachment" class="msg-attachment-img" onclick="window.open('${msg.file_path}', '_blank')">`;
    } else if (msg.message_type === 'file' && msg.file_path) {
      attachmentHtml = `
        <a href="${msg.file_path}" download="${msg.file_name}" class="msg-file-card">
          <i class="bi bi-file-earmark-arrow-down-fill msg-file-icon"></i>
          <div class="msg-file-meta">
            <span class="msg-file-name">${this.escapeHtml(msg.file_name || 'Download File')}</span>
            <span class="msg-file-size">${this.formatBytes(msg.file_size)}</span>
          </div>
        </a>
      `;
    }

    const showSenderName = !isMine && currentConversation && currentConversation.is_group;

    row.innerHTML = `
      ${!isMine ? `<img src="${msg.sender_avatar}" alt="${msg.sender_name}" class="msg-avatar">` : ''}
      <div class="msg-bubble-wrap">
        ${showSenderName ? `<span class="msg-sender-name">${this.escapeHtml(msg.sender_name)}</span>` : ''}
        <div class="msg-bubble ${msg.is_deleted ? 'deleted' : ''}" id="msg-bubble-${msg.id}">
          ${attachmentHtml}
          ${msg.is_deleted ? '<em>This message was deleted</em>' : `<span id="msg-text-${msg.id}">${this.escapeHtml(msg.text)}</span>`}
          ${msg.is_edited ? '<span class="msg-edited-tag">(edited)</span>' : ''}
          <div class="msg-meta">
            <span>${msg.timestamp_str}</span>
            ${isMine && !msg.is_deleted ? `<span class="${tickClass}" data-msg-id="${msg.id}">${statusIcon}</span>` : ''}
          </div>
        </div>
      </div>
      ${isMine && !msg.is_deleted ? `
        <div class="msg-actions-trigger" onclick="ChatApp.openMessageActionMenu(${msg.id}, event)">
          <i class="bi bi-three-dots-vertical"></i>
        </div>
      ` : ''}
    `;

    return row;
  },

  appendMessage(msg) {
    const feed = document.getElementById('chat-messages-area');
    if (!feed) return;
    const row = this.createMessageRowElement(msg);
    feed.appendChild(row);
  },

  sendMessage() {
    const input = document.getElementById('message-input');
    if (!input || !window.currentConversationId) return;

    const text = input.value.trim();
    if (!text) return;

    // Stop typing indicator
    if (socket) {
      socket.emit('stop_typing', { conversation_id: window.currentConversationId });
      isTyping = false;
    }

    // Check if currently editing a message
    if (currentEditingMessageId) {
      if (socket) {
        socket.emit('edit_message', {
          message_id: currentEditingMessageId,
          text: text
        });
      }
      this.cancelEditMode();
      return;
    }

    // Send via socket
    if (socket) {
      socket.emit('send_message', {
        conversation_id: window.currentConversationId,
        text: text,
        message_type: 'text'
      });
    }

    input.value = '';
    input.style.height = 'auto';
  },

  async handleFileSelected(file) {
    if (!file || !window.currentConversationId) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('caption', file.name);

    showOmniToast('Uploading', `Uploading ${file.name}...`, 'bi-cloud-arrow-up');

    try {
      const res = await fetch(`/api/conversations/${window.currentConversationId}/upload`, {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        const msg = await res.json();
        // Emit via socket to inform other participants immediately
        if (socket) {
          socket.emit('send_message', {
            conversation_id: window.currentConversationId,
            text: msg.text,
            message_type: msg.message_type,
            file_path: msg.file_path,
            file_name: msg.file_name,
            file_size: msg.file_size
          });
        }
      } else {
        alert("File upload failed");
      }
    } catch (err) {
      console.error("Upload error:", err);
    }
  },

  handleTypingInput() {
    if (!socket || !window.currentConversationId) return;

    if (!isTyping) {
      isTyping = true;
      socket.emit('typing', { conversation_id: window.currentConversationId });
    }

    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
      isTyping = false;
      socket.emit('stop_typing', { conversation_id: window.currentConversationId });
    }, 2500);
  },

  openMessageActionMenu(msgId, event) {
    event.stopPropagation();
    const action = confirm("Choose an action:\n\nOK: Edit Message\nCancel: Delete for Everyone");
    if (action) {
      this.startEditMode(msgId);
    } else {
      if (confirm("Are you sure you want to delete this message for everyone?")) {
        if (socket) {
          socket.emit('delete_message', { message_id: msgId });
        }
      }
    }
  },

  startEditMode(msgId) {
    currentEditingMessageId = msgId;
    const msgTextEl = document.getElementById(`msg-text-${msgId}`);
    const input = document.getElementById('message-input');
    const strip = document.getElementById('file-preview-strip');

    if (msgTextEl && input && strip) {
      input.value = msgTextEl.textContent.trim();
      input.focus();
      strip.className = 'file-preview-strip show';
      strip.innerHTML = `
        <i class="bi bi-pencil-fill" style="color: var(--primary);"></i>
        <span>Editing message...</span>
        <button type="button" class="btn btn-sm" onclick="ChatApp.cancelEditMode()" style="margin-left: auto; border: none; background: none; color: var(--text-muted); cursor: pointer;">Cancel</button>
      `;
    }
  },

  cancelEditMode() {
    currentEditingMessageId = null;
    const input = document.getElementById('message-input');
    const strip = document.getElementById('file-preview-strip');
    if (input) input.value = '';
    if (strip) {
      strip.className = 'file-preview-strip';
      strip.innerHTML = '';
    }
  },

  updateConversationCard(msg) {
    const snippet = document.getElementById(`snippet-${msg.conversation_id}`);
    if (snippet) {
      snippet.textContent = msg.text || 'Attachment';
    }
  },

  filterConversations(query) {
    const items = document.querySelectorAll('.conv-item');
    items.forEach(item => {
      const name = item.querySelector('.conv-name')?.textContent.toLowerCase() || '';
      const snippet = item.querySelector('.conv-snippet')?.textContent.toLowerCase() || '';
      if (name.includes(query) || snippet.includes(query)) {
        item.style.display = 'flex';
      } else {
        item.style.display = 'none';
      }
    });
  },

  filterChatMessages(query) {
    const rows = document.querySelectorAll('.msg-row');
    rows.forEach(r => {
      const text = r.querySelector('.msg-bubble')?.textContent.toLowerCase() || '';
      if (!query || text.includes(query)) {
        r.style.display = 'flex';
      } else {
        r.style.display = 'none';
      }
    });
  },

  // Group Management Modals & Actions
  async createGroupChat() {
    const nameInput = document.getElementById('group-name-input');
    const descInput = document.getElementById('group-desc-input');
    const checkboxes = document.querySelectorAll('.group-member-checkbox:checked');

    const name = nameInput.value.trim();
    if (!name) {
      alert("Please enter a group name");
      return;
    }

    const memberIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

    try {
      const res = await fetch('/api/conversations/group', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description: descInput.value.trim(), member_ids: memberIds })
      });

      if (res.ok) {
        const newGroup = await res.json();
        document.getElementById('create-group-modal').classList.remove('show');
        nameInput.value = '';
        descInput.value = '';
        await this.loadConversations();
        this.selectConversation(newGroup.id);
        showOmniToast('Group Created', `Group "${newGroup.name}" is ready!`, 'bi-people-fill');
      }
    } catch (err) {
      console.error("Create group error:", err);
    }
  },

  async startDirectChat(userId) {
    try {
      const res = await fetch(`/api/conversations/direct/${userId}`, { method: 'POST' });
      if (res.ok) {
        const conv = await res.json();
        document.getElementById('new-direct-modal').classList.remove('show');
        await this.loadConversations();
        this.selectConversation(conv.id);
      }
    } catch (err) {
      console.error("Direct chat error:", err);
    }
  },

  openGroupDetailsModal() {
    if (!currentConversation || !currentConversation.is_group) return;

    const modal = document.getElementById('group-details-modal');
    const titleEl = document.getElementById('gmodal-group-name');
    const descEl = document.getElementById('gmodal-group-desc');
    const listEl = document.getElementById('gmodal-members-list');
    const adminControls = document.getElementById('gmodal-admin-controls');

    titleEl.textContent = currentConversation.name;
    descEl.textContent = currentConversation.description || 'No description provided';
    listEl.innerHTML = '';

    if (currentConversation.is_admin) {
      adminControls.style.display = 'block';
    } else {
      adminControls.style.display = 'none';
    }

    currentConversation.members.forEach(m => {
      const mRow = document.createElement('div');
      mRow.className = 'd-flex align-items-center justify-content-between p-2 mb-1 rounded';
      mRow.style.backgroundColor = 'var(--bg-input)';
      mRow.innerHTML = `
        <div class="d-flex align-items-center gap-2">
          <img src="${m.avatar_url}" style="width: 32px; height: 32px; border-radius: 50%;">
          <div>
            <div style="font-weight: 600; font-size: 0.85rem;">
              ${this.escapeHtml(m.username)}
              ${m.is_admin ? '<span class="badge bg-primary" style="font-size: 0.65rem;">Admin</span>' : ''}
            </div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${m.is_online ? 'Online' : 'Offline'}</div>
          </div>
        </div>
        ${currentConversation.is_admin && m.user_id != this.currentUserId ? `
          <button class="btn btn-sm btn-outline-danger" onclick="ChatApp.removeGroupMember(${m.user_id})" style="font-size: 0.75rem; padding: 0.2rem 0.5rem;">Remove</button>
        ` : ''}
      `;
      listEl.appendChild(mRow);
    });

    modal.classList.add('show');
  },

  async addGroupMember() {
    const select = document.getElementById('select-add-member');
    const userId = select.value;
    if (!userId || !window.currentConversationId) return;

    try {
      const res = await fetch(`/api/conversations/${window.currentConversationId}/members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: parseInt(userId) })
      });
      if (res.ok) {
        showOmniToast('Member Added', 'User added to group', 'bi-person-check-fill');
        this.selectConversation(window.currentConversationId);
        document.getElementById('group-details-modal').classList.remove('show');
      }
    } catch (err) {
      console.error(err);
    }
  },

  async removeGroupMember(userId) {
    if (!confirm("Remove this user from the group?")) return;
    try {
      const res = await fetch(`/api/conversations/${window.currentConversationId}/members/${userId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        showOmniToast('Member Removed', 'User was removed from group', 'bi-person-x-fill');
        this.selectConversation(window.currentConversationId);
        document.getElementById('group-details-modal').classList.remove('show');
      }
    } catch (err) {
      console.error(err);
    }
  },

  async leaveCurrentGroup() {
    if (!confirm("Are you sure you want to leave this group?")) return;
    try {
      const res = await fetch(`/api/conversations/${window.currentConversationId}/leave`, {
        method: 'POST'
      });
      if (res.ok) {
        document.getElementById('group-details-modal').classList.remove('show');
        window.currentConversationId = null;
        await this.loadConversations();
      }
    } catch (err) {
      console.error(err);
    }
  },

  scrollToBottom() {
    const feed = document.getElementById('chat-messages-area');
    if (feed) {
      setTimeout(() => {
        feed.scrollTop = feed.scrollHeight;
      }, 50);
    }
  },

  escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },

  formatBytes(bytes) {
    if (!bytes) return '';
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / 1048576).toFixed(1) + ' MB';
  },

  formatDateHeader(dateStr) {
    const today = new Date().toISOString().split('T')[0];
    const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
    if (dateStr === today) return 'Today';
    if (dateStr === yesterday) return 'Yesterday';
    return dateStr;
  }
};
