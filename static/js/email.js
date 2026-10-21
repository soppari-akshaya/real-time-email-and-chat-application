// Member 1: Email Interface Controller

const EmailApp = {
  currentFolder: 'inbox',

  init(folder = 'inbox') {
    this.currentFolder = folder;
    this.bindEvents();
    this.loadEmails();
  },

  bindEvents() {
    const searchInput = document.getElementById('email-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.loadEmails(e.target.value.trim());
      });
    }

    const composeBtn = document.getElementById('btn-open-compose');
    const composeModal = document.getElementById('compose-email-modal');
    if (composeBtn && composeModal) {
      composeBtn.addEventListener('click', () => {
        composeModal.classList.add('show');
      });
    }

    const closeComposeBtn = document.getElementById('close-compose-btn');
    if (closeComposeBtn && composeModal) {
      closeComposeBtn.addEventListener('click', () => {
        composeModal.classList.remove('show');
      });
    }

    const composeForm = document.getElementById('compose-email-form');
    if (composeForm) {
      composeForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.sendEmail(new FormData(composeForm));
      });
    }
  },

  async loadEmails(query = '') {
    const listContainer = document.getElementById('email-list-container');
    if (!listContainer) return;

    try {
      let url = `/api/emails?folder=${this.currentFolder}`;
      if (query) url += `&q=${encodeURIComponent(query)}`;

      const res = await fetch(url);
      const emails = await res.json();

      listContainer.innerHTML = '';
      if (emails.length === 0) {
        listContainer.innerHTML = `
          <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
            <i class="bi bi-inbox" style="font-size: 2.5rem; display: block; margin-bottom: 0.5rem;"></i>
            No emails found in this folder.
          </div>
        `;
        return;
      }

      emails.forEach(e => {
        const row = document.createElement('div');
        row.className = `email-row-item ${!e.is_read ? 'unread' : ''}`;
        row.innerHTML = `
          <button class="star-btn ${e.is_starred ? 'active' : ''}" onclick="EmailApp.toggleStar(${e.id}, event)">
            <i class="bi bi-star${e.is_starred ? '-fill' : ''}"></i>
          </button>
          <button class="important-btn ${e.is_important ? 'active' : ''}" onclick="EmailApp.toggleImportant(${e.id}, event)">
            <i class="bi bi-tag${e.is_important ? '-fill' : ''}"></i>
          </button>
          <div class="email-sender-col">${e.sender_name}</div>
          <div class="email-content-col">
            <span class="email-subject-line">${e.subject}</span>
            <span class="email-snippet-line"> - ${e.body || ''}</span>
            ${e.attachments.length > 0 ? '<i class="bi bi-paperclip" title="Has attachments"></i>' : ''}
          </div>
          <div class="email-date-col">${e.date_str}</div>
        `;
        row.onclick = () => this.viewEmail(e);
        listContainer.appendChild(row);
      });
    } catch (err) {
      console.error("Error loading emails:", err);
    }
  },

  async toggleStar(emailId, event) {
    event.stopPropagation();
    try {
      const res = await fetch(`/api/emails/${emailId}/toggle-star`, { method: 'POST' });
      if (res.ok) {
        this.loadEmails();
      }
    } catch (err) {
      console.error(err);
    }
  },

  async toggleImportant(emailId, event) {
    event.stopPropagation();
    try {
      const res = await fetch(`/api/emails/${emailId}/toggle-important`, { method: 'POST' });
      if (res.ok) {
        this.loadEmails();
      }
    } catch (err) {
      console.error(err);
    }
  },

  viewEmail(email) {
    const modal = document.getElementById('view-email-modal');
    if (!modal) return;

    document.getElementById('view-email-subject').textContent = email.subject;
    document.getElementById('view-email-sender').textContent = `From: ${email.sender_name} (${email.sender_email})`;
    document.getElementById('view-email-to').textContent = `To: ${email.recipient_emails}`;
    document.getElementById('view-email-date').textContent = email.date_str;
    document.getElementById('view-email-body').textContent = email.body;

    const attArea = document.getElementById('view-email-attachments');
    attArea.innerHTML = '';
    if (email.attachments && email.attachments.length > 0) {
      email.attachments.forEach(a => {
        const aCard = document.createElement('a');
        aCard.href = a.file_path;
        aCard.download = a.filename;
        aCard.className = 'btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1 me-2 mb-2';
        aCard.innerHTML = `<i class="bi bi-file-earmark-arrow-down"></i> ${a.filename}`;
        attArea.appendChild(aCard);
      });
    }

    modal.classList.add('show');
  },

  async sendEmail(formData) {
    try {
      const res = await fetch('/api/emails/compose', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        showOmniToast('Email Sent', 'Your email was dispatched successfully!', 'bi-send-check-fill');
        document.getElementById('compose-email-modal').classList.remove('show');
        document.getElementById('compose-email-form').reset();
        this.loadEmails();
      } else {
        alert("Failed to send email");
      }
    } catch (err) {
      console.error(err);
    }
  }
};
