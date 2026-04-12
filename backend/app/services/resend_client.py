import base64
import logging
from datetime import datetime

import requests

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
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {Config.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": Config.RESEND_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html,
            "attachments": [
                {
                    "filename": attachment_name,
                    "content": base64.b64encode(png_bytes).decode("ascii"),
                }
            ],
        },
        timeout=30,
    )
    if response.status_code >= 400:
        logger.error("Resend email failed: %s", response.text)
        response.raise_for_status()
