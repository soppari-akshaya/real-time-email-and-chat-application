import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, current_app, url_for
from werkzeug.utils import secure_filename
from models import db, User, Email, EmailAttachment
from routes.auth import login_required, get_current_user

email_bp = Blueprint('email', __name__)

@email_bp.route('/email')
@email_bp.route('/mailbox')
@login_required
def mailbox_view():
    user = get_current_user()
    folder = request.args.get('folder', 'inbox')
    return render_template('email.html', current_user=user, current_folder=folder)

@email_bp.route('/api/emails', methods=['GET'])
@login_required
def get_emails():
    user = get_current_user()
    folder = request.args.get('folder', 'inbox')
    filter_star = request.args.get('starred') == 'true'
    filter_important = request.args.get('important') == 'true'
    query = request.args.get('q', '').strip()

    emails_query = Email.query

    if folder == 'sent':
        emails_query = emails_query.filter_by(sender_id=user.id, folder='sent')
    elif folder == 'drafts':
        emails_query = emails_query.filter_by(sender_id=user.id, folder='drafts')
    elif folder == 'trash':
        emails_query = emails_query.filter(
            ((Email.recipient_emails.ilike(f'%{user.email}%')) | (Email.sender_id == user.id)),
            Email.folder == 'trash'
        )
    else:  # inbox
        emails_query = emails_query.filter(
            Email.recipient_emails.ilike(f'%{user.email}%'),
            Email.folder == 'inbox'
        )

    if filter_star:
        emails_query = emails_query.filter_by(is_starred=True)
    if filter_important:
        emails_query = emails_query.filter_by(is_important=True)

    if query:
        emails_query = emails_query.filter(
            (Email.subject.ilike(f'%{query}%')) |
            (Email.body.ilike(f'%{query}%')) |
            (Email.recipient_emails.ilike(f'%{query}%'))
        )

    emails = emails_query.order_by(Email.created_at.desc()).all()
    return jsonify([e.to_dict() for e in emails])

@email_bp.route('/api/emails/compose', methods=['POST'])
@login_required
def compose_email():
    user = get_current_user()
    
    recipients = request.form.get('recipients', '').strip()
    subject = request.form.get('subject', '').strip() or "(No Subject)"
    body = request.form.get('body', '').strip()
    is_draft = request.form.get('is_draft') == 'true'
    folder = 'drafts' if is_draft else 'sent'

    if not recipients and not is_draft:
        return jsonify({'error': 'Recipient email is required'}), 400

    new_email = Email(
        sender_id=user.id,
        recipient_emails=recipients,
        subject=subject,
        body=body,
        folder=folder
    )
    db.session.add(new_email)
    db.session.flush()

    # If sending to actual recipients who are registered users, also create inbox copy
    if not is_draft:
        recipient_list = [r.strip() for r in recipients.split(',') if r.strip()]
        for r_email in recipient_list:
            inbox_copy = Email(
                sender_id=user.id,
                recipient_emails=recipients,
                subject=subject,
                body=body,
                folder='inbox'
            )
            db.session.add(inbox_copy)

    # Process attachments
    if 'attachments' in request.files:
        files = request.files.getlist('attachments')
        for f in files:
            if f and f.filename != '':
                filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{f.filename}")
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                f.save(file_path)
                file_size = os.path.getsize(file_path)
                rel_url = url_for('static', filename=f'uploads/{filename}')
                att = EmailAttachment(
                    email_id=new_email.id,
                    filename=f.filename,
                    file_path=rel_url,
                    file_size=file_size,
                    file_type=f.content_type
                )
                db.session.add(att)

    db.session.commit()
    return jsonify(new_email.to_dict()), 201

@email_bp.route('/api/emails/<int:email_id>/toggle-star', methods=['POST'])
@login_required
def toggle_star(email_id):
    email = Email.query.get_or_404(email_id)
    email.is_starred = not email.is_starred
    db.session.commit()
    return jsonify({'is_starred': email.is_starred})

@email_bp.route('/api/emails/<int:email_id>/toggle-important', methods=['POST'])
@login_required
def toggle_important(email_id):
    email = Email.query.get_or_404(email_id)
    email.is_important = not email.is_important
    db.session.commit()
    return jsonify({'is_important': email.is_important})

@email_bp.route('/api/emails/<int:email_id>/move', methods=['POST'])
@login_required
def move_email(email_id):
    email = Email.query.get_or_404(email_id)
    data = request.get_json() or {}
    new_folder = data.get('folder', 'trash')
    email.folder = new_folder
    db.session.commit()
    return jsonify({'folder': email.folder})
