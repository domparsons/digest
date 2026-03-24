import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from newsdigest.models import Article, RankedArticle

logger = logging.getLogger(__name__)

_TIER_ORDER = ["highlight", "notable", "routine"]
_TIER_LABELS = {"highlight": "★ Highlights", "notable": "Notable", "routine": "Routine"}
_TIER_COLORS = {"highlight": "#7c3aed", "notable": "#1d4ed8", "routine": "#6b7280"}


class EmailOutput:
    """Send a digest via SMTP email."""

    def __init__(self, recipient: str) -> None:
        self.recipient = recipient
        self.smtp_host = os.environ.get("NEWSDIGEST_SMTP_HOST", "")
        self.smtp_port = int(os.environ.get("NEWSDIGEST_SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("NEWSDIGEST_SMTP_USER", "")
        self.smtp_pass = os.environ.get("NEWSDIGEST_SMTP_PASS", "")

    def render(self, articles: list[Article]) -> None:
        self._send(self._build_html(articles), len(articles))

    def render_ranked(self, ranked: list[RankedArticle]) -> None:
        self._send(self._build_ranked_html(ranked), len(ranked))

    def _send(self, html: str, count: int) -> None:
        if not self.smtp_host:
            logger.error("NEWSDIGEST_SMTP_HOST not set — skipping email output.")
            return

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

        logger.info("Digest email sent to %s (%d articles)", self.recipient, count)

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
                f"<small style='color:#666'>{meta}</small>"
                f"{summary_html}</td></tr>"
            )

        return (
            "<html><body style='font-family:sans-serif;max-width:700px;margin:0 auto'>"
            f"<h2>News Digest &mdash; {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>"
            f"<table style='width:100%;border-collapse:collapse'>{''.join(rows)}</table>"
            f"<p><em>{len(articles)} new article(s)</em></p>"
            "</body></html>"
        )

    def _build_ranked_html(self, ranked: list[RankedArticle]) -> str:
        if not ranked:
            return "<html><body><p>No new articles.</p></body></html>"

        by_tier: dict[str, list[RankedArticle]] = {t: [] for t in _TIER_ORDER}
        for ra in ranked:
            by_tier.setdefault(ra.tier, []).append(ra)

        sections: list[str] = []
        total = 0
        for tier in _TIER_ORDER:
            tier_articles = sorted(by_tier[tier], key=lambda r: r.score, reverse=True)
            if not tier_articles:
                continue
            color = _TIER_COLORS.get(tier, "#333")
            label = _TIER_LABELS.get(tier, tier.title())
            rows: list[str] = []
            for ra in tier_articles:
                article = ra.article
                meta_parts: list[str] = [article.source]
                if article.category:
                    meta_parts.append(article.category)
                if article.published:
                    meta_parts.append(article.published.strftime("%Y-%m-%d %H:%M"))
                meta = " &middot; ".join(meta_parts)
                summary_html = ""
                if ra.summary and ra.summary.strip().lower() != article.title.strip().lower():
                    summary_html = f"<p style='margin:4px 0 0;color:#444'>{ra.summary}</p>"
                rows.append(
                    f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>"
                    f"<strong><a href='{article.url}' style='color:#111'>{article.title}</a>"
                    f"</strong><br>"
                    f"<small style='color:#666'>{meta}</small>"
                    f"{summary_html}</td></tr>"
                )
            sections.append(
                f"<h3 style='color:{color};border-bottom:2px solid {color};padding-bottom:4px'>"
                f"{label}</h3>"
                f"<table style='width:100%;border-collapse:collapse'>{''.join(rows)}</table>"
            )
            total += len(tier_articles)

        return (
            "<html><body style='font-family:sans-serif;max-width:700px;margin:0 auto'>"
            f"<h2>News Digest &mdash; {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>"
            f"{''.join(sections)}"
            f"<p><em>{total} article(s)</em></p>"
            "</body></html>"
        )
