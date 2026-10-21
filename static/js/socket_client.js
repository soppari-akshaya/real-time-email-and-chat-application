// OmniSync Global Socket.IO Manager
let socket = null;

function initSocketConnection() {
  if (typeof io === 'undefined') {
    console.error("Socket.io library not loaded");
    return;
  }

  socket = io({
    transports: ['websocket', 'polling']
  });

  socket.on('connect', () => {
    console.log("⚡ Connected to OmniSync Real-Time Gateway");
  });

  // Global Presence updates
  socket.on('user_status_changed', (data) => {
    const { user_id, is_online, last_seen } = data;
    
    // Update presence dot on all elements with data-user-id
    const presenceDots = document.querySelectorAll(`.user-presence-${user_id}`);
    presenceDots.forEach(dot => {
      if (is_online) {
        dot.classList.remove('offline');
        dot.classList.add('online');
      } else {
        dot.classList.remove('online');
        dot.classList.add('offline');
      }
    });

    // Update active chat status if viewing this user
    const activeChatStatus = document.getElementById('active-chat-status');
    if (activeChatStatus && activeChatStatus.dataset.otherUserId == user_id) {
      if (is_online) {
        activeChatStatus.className = 'active-chat-status online';
        activeChatStatus.innerHTML = '<i class="bi bi-circle-fill" style="font-size: 8px;"></i> Online';
      } else {
        activeChatStatus.className = 'active-chat-status';
        activeChatStatus.innerHTML = 'Offline';
      }
    }
  });

  // Global In-App Notifications
  socket.on('notification', (data) => {
    // If not currently in this conversation, notify the user!
    const activeConvId = window.currentConversationId;
    if (activeConvId != data.conversation_id) {
      showOmniToast(
        data.conversation_name || data.sender_name,
        `${data.sender_name}: ${data.text}`,
        'bi-chat-left-text-fill'
      );

      // Increment sidebar badge if conversation exists in list
      const badge = document.getElementById(`badge-${data.conversation_id}`);
      if (badge) {
        let count = parseInt(badge.textContent || '0') + 1;
        badge.textContent = count;
        badge.style.display = 'inline-block';
      }
    }
  });

  socket.on('disconnect', () => {
    console.log("Disconnected from real-time gateway");
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initSocketConnection();
});
