import base64
import logging
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import Config

logger = logging.getLogger(__name__)


def send_completion_email(
    to_email: str,
    city: str,
    country: str,
    theme: str,
    signed_url: str,
    png_bytes: bytes,
    generated_at: datetime,
) -> None:
    subject = f"Your {city} map poster is ready"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5; color: #111827;">
      <h2 style="margin-bottom: 12px;">Your map poster is ready</h2>
      <p><strong>City:</strong> {city}, {country}</p>
      <p><strong>Theme:</strong> {theme}</p>
      <p><strong>Generated:</strong> {generated_at.strftime("%Y-%m-%d %H:%M UTC")}</p>
      <p>
        <a href="{signed_url}" style="display: inline-block; padding: 10px 16px; background: #111827; color: #ffffff; text-decoration: none; border-radius: 6px;">
          Download (link valid 7 days)
        </a>
      </p>
      <p>The PNG is also attached to this email.</p>
    </div>
    """.strip()

    attachment_name = f"{city.strip().lower().replace(' ', '_')}_{theme}.png"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = Config.GMAIL_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    attachment = MIMEApplication(png_bytes, Name=attachment_name)
    attachment["Content-Disposition"] = f'attachment; filename="{attachment_name}"'
    msg.attach(attachment)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(Config.GMAIL_FROM, Config.GMAIL_APP_PASSWORD)
        smtp.sendmail(Config.GMAIL_FROM, to_email, msg.as_string())
        logger.info("Email sent to %s via Gmail SMTP", to_email)
