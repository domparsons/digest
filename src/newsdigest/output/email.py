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

_TIER_STYLES = {
    "highlight": {
        "border": "#d97706",
        "bg": "#fffbeb",
        "header_bg": "#d97706",
        "header_color": "#ffffff",
    },
    "notable": {
        "border": "#e2e8f0",
        "bg": "#f8fafc",
        "header_bg": "#1e293b",
        "header_color": "#ffffff",
    },
    "routine": {
        "border": "#e2e8f0",
        "bg": "#ffffff",
        "header_bg": "#64748b",
        "header_color": "#ffffff",
    },
}

_BASE_STYLES = (
    "body{margin:0;padding:0;background:#f1f5f9;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}"
    ".wrapper{max-width:640px;margin:0 auto;padding:24px 16px}"
    ".header{margin-bottom:24px}"
    ".header h1{margin:0 0 4px;font-size:22px;color:#0f172a;letter-spacing:-0.3px}"
    ".header p{margin:0;font-size:13px;color:#64748b}"
    ".section{margin-bottom:20px}"
    ".section-header{padding:8px 14px;font-size:12px;font-weight:700;"
    "letter-spacing:0.8px;text-transform:uppercase}"
    ".article{padding:14px;border-left:3px solid transparent;border-bottom:1px solid #e2e8f0}"
    ".article:last-child{border-bottom:none;border-radius:0 0 6px 6px}"
    ".article-title{margin:0 0 5px;font-size:15px;font-weight:600;line-height:1.4}"
    ".article-title a{text-decoration:none;color:#0f172a}"
    ".article-meta{font-size:12px;color:#94a3b8;margin:0 0 6px}"
    ".article-summary{font-size:13px;color:#475569;margin:6px 0 0;line-height:1.5}"
    ".footer{margin-top:24px;font-size:12px;color:#94a3b8;text-align:center}"
)


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
        msg["Subject"] = f"News Digest — {datetime.now().strftime('%a %d %b %Y')}"
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
            return _wrap("", "<p style='color:#64748b'>No new articles.</p>")

        cards = "".join(self._article_card(a, border="#e2e8f0", bg="#ffffff") for a in articles)
        section = f"""
        <div class='section'>
          <div style='background:#1e293b;border-radius:6px 6px 0 0'>
            <div class='section-header' style='color:#fff'>All Articles</div>
          </div>
          <div style='border:1px solid #e2e8f0;border-top:none;border-radius:0 0 6px 6px'>
            {cards}
          </div>
        </div>"""
        return _wrap(f"{len(articles)} article(s)", section)

    def _build_ranked_html(self, ranked: list[RankedArticle]) -> str:
        if not ranked:
            return _wrap("", "<p style='color:#64748b'>No new articles.</p>")

        by_tier: dict[str, list[RankedArticle]] = {t: [] for t in _TIER_ORDER}
        for ra in ranked:
            by_tier.setdefault(ra.tier, []).append(ra)

        sections: list[str] = []
        total = 0
        for tier in _TIER_ORDER:
            tier_articles = sorted(by_tier[tier], key=lambda r: r.score, reverse=True)
            if not tier_articles:
                continue
            s = _TIER_STYLES[tier]
            label = _TIER_LABELS.get(tier, tier.title())
            cards = "".join(
                self._ranked_card(ra, border=s["border"], bg=s["bg"]) for ra in tier_articles
            )
            sections.append(f"""
            <div class='section'>
              <div style='background:{s["header_bg"]};border-radius:6px 6px 0 0'>
                <div class='section-header' style='color:{s["header_color"]}'>{label}</div>
              </div>
              <div style='border:1px solid {s["border"]};border-top:none;border-radius:0 0 6px 6px'>
                {cards}
              </div>
            </div>""")
            total += len(tier_articles)

        return _wrap(f"{total} article(s)", "".join(sections))

    def _article_card(self, article: Article, *, border: str, bg: str) -> str:
        meta = self._meta(article.source, article.category, article.published)
        summary_html = (
            f"<p class='article-summary'>{article.summary}</p>" if article.summary else ""
        )
        return f"""
        <div class='article' style='border-left-color:{border};background:{bg}'>
          <p class='article-title'><a href='{article.url}'>{article.title}</a></p>
          <p class='article-meta'>{meta}</p>
          {summary_html}
        </div>"""

    def _ranked_card(self, ra: RankedArticle, *, border: str, bg: str) -> str:
        article = ra.article
        meta = self._meta(article.source, article.category, article.published)
        summary_html = ""
        if ra.summary and ra.summary.strip().lower() != article.title.strip().lower():
            summary_html = f"<p class='article-summary'>{ra.summary}</p>"
        return f"""
        <div class='article' style='border-left-color:{border};background:{bg}'>
          <p class='article-title'><a href='{article.url}'>{article.title}</a></p>
          <p class='article-meta'>{meta}</p>
          {summary_html}
        </div>"""

    def _meta(self, source: str, category: str, published: datetime | None) -> str:
        parts = [source]
        if category:
            parts.append(category)
        if published:
            parts.append(published.strftime("%d %b %Y"))
        return " &middot; ".join(parts)


def _wrap(footer_text: str, body: str) -> str:
    now = datetime.now().strftime("%A %d %B %Y")
    footer = f"<div class='footer'>{footer_text}</div>" if footer_text else ""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><style>{_BASE_STYLES}</style></head>
<body>
  <div class='wrapper'>
    <div class='header'>
      <h1>News Digest</h1>
      <p>{now}</p>
    </div>
    {body}
    {footer}
  </div>
</body>
</html>"""
