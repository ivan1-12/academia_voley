import smtplib
from email.message import EmailMessage
from flask import current_app
from utils.task_queue import enqueue_task


def _send_email_sync(to_address, subject, body):
    cfg = current_app.config
    smtp_host = cfg.get("SMTP_HOST")
    smtp_port = int(cfg.get("SMTP_PORT", 0)) if cfg.get("SMTP_PORT") else None
    smtp_user = cfg.get("SMTP_USER")
    smtp_pass = cfg.get("SMTP_PASSWORD")
    from_addr = cfg.get("EMAIL_FROM", cfg.get("ADMIN_EMAIL"))

    if not smtp_host or not smtp_port:
        current_app.logger.info("SMTP no configurado: no se envía correo a %s", to_address)
        return False

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_address
        msg.set_content(body)

        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        current_app.logger.info("Correo enviado a %s (subject=%s)", to_address, subject)
        return True
    except Exception as e:
        current_app.logger.exception("Error enviando correo a %s: %s", to_address, e)
        return False


def send_email(to_address, subject, body, async_send=True):
    """Envía un correo, preferentemente en segundo plano."""
    if async_send:
        enqueue_task(_send_email_sync, to_address, subject, body)
        return True
    return _send_email_sync(to_address, subject, body)
