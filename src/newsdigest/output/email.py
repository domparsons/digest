import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from newsdigest.models import Article

logger = logging.getLogger(__name__)


class EmailOutput:
    """Send a digest via SMTP email."""

    def __init__(self, recipient: str) -> None:
        self.recipient = recipient
        self.smtp_host = os.environ.get("NEWSDIGEST_SMTP_HOST", "")
        self.smtp_port = int(os.environ.get("NEWSDIGEST_SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("NEWSDIGEST_SMTP_USER", "")
        self.smtp_pass = os.environ.get("NEWSDIGEST_SMTP_PASS", "")

    def render(self, articles: list[Article]) -> None:
        if not self.smtp_host:
            logger.error("NEWSDIGEST_SMTP_HOST not set — skipping email output.")
            return

        html = self._build_html(articles)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"News Digest — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg["From"] = self.smtp_user
        msg["To"] = self.recipient
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            if self.smtp_user and self.smtp_pass:
                server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.smtp_user, [self.recipient], msg.as_string())

        logger.info("Digest email sent to %s", self.recipient)

    def _build_html(self, articles: list[Article]) -> str:
        if not articles:
            return "<html><body><p>No new articles.</p></body></html>"

        rows: list[str] = []
        for article in articles:
            meta_parts: list[str] = [article.source]
            if article.published:
                meta_parts.append(article.published.strftime("%Y-%m-%d %H:%M"))
            meta = " &middot; ".join(meta_parts)

            summary_html = f"<p>{article.summary}</p>" if article.summary else ""
            rows.append(
                f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>"
                f"<strong><a href='{article.url}'>{article.title}</a></strong><br>"
                f"<small>{meta}</small>"
                f"{summary_html}"
                f"</td></tr>"
            )

        return (
            "<html><body>"
            f"<h2>News Digest &mdash; {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>"
            f"<table style='width:100%;border-collapse:collapse'>{''.join(rows)}</table>"
            f"<p><em>{len(articles)} new article(s)</em></p>"
            "</body></html>"
        )
