"""Build and send the daily HTML email digest via SendGrid."""
from __future__ import annotations

import os
from datetime import datetime
from jinja2 import Environment, BaseLoader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from .models import MatchSummary

_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px; }
    .container { max-width: 640px; margin: auto; background: #fff; border-radius: 8px; overflow: hidden; }
    .header { background: #004f9e; color: #fff; padding: 24px; text-align: center; }
    .header h1 { margin: 0; font-size: 22px; }
    .header p  { margin: 4px 0 0; font-size: 13px; opacity: .8; }
    .match-block { padding: 16px 24px; border-bottom: 1px solid #eee; }
    .match-title { font-size: 16px; font-weight: bold; color: #004f9e; margin-bottom: 4px; }
    .match-meta  { font-size: 12px; color: #888; margin-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { text-align: left; background: #f0f4f8; padding: 6px 8px; }
    td { padding: 6px 8px; border-bottom: 1px solid #f0f0f0; }
    .price { color: #1a7c3e; font-weight: bold; }
    .footer { text-align: center; padding: 16px; font-size: 11px; color: #aaa; }
    a { color: #004f9e; }
  </style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>⚽ World Cup 2026 Ticket Digest</h1>
    <p>{{ today }} — Cheapest listings from StubHub &amp; SeatGeek</p>
  </div>

  {% for summary in summaries %}
  <div class="match-block">
    <div class="match-title">{{ summary.match }}</div>
    <div class="match-meta">{{ summary.venue }} &bull; {{ summary.match_date.strftime('%b %d, %Y %H:%M UTC') }}</div>
    {% if summary.cheapest_listings %}
    <table>
      <tr>
        <th>Source</th><th>Section</th><th>Row</th><th>Qty</th><th>Price</th><th>Link</th>
      </tr>
      {% for t in summary.cheapest_listings %}
      <tr>
        <td>{{ t.source }}</td>
        <td>{{ t.section }}</td>
        <td>{{ t.row }}</td>
        <td>{{ t.quantity }}</td>
        <td class="price">${{ "%.2f"|format(t.price_usd) }}</td>
        <td><a href="{{ t.url }}">Buy</a></td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <p style="color:#aaa;font-size:13px;">No listings found under your price cap today.</p>
    {% endif %}
  </div>
  {% endfor %}

  <div class="footer">
    You are receiving this because you subscribed to the World Cup 2026 Ticket Tracker.<br>
    Prices are updated daily. All prices in USD and include fees where shown.
  </div>
</div>
</body>
</html>
"""


def render_digest(summaries: list[MatchSummary]) -> str:
    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(_TEMPLATE)
    return tmpl.render(summaries=summaries, today=datetime.utcnow().strftime("%A, %B %d %Y"))


def send_digest(summaries: list[MatchSummary]) -> None:
    api_key = os.environ["SENDGRID_API_KEY"]
    from_email = os.environ["FROM_EMAIL"]
    subscribers = [s.strip() for s in os.getenv("SUBSCRIBERS", "").split(",") if s.strip()]

    if not subscribers:
        print("[digest] No subscribers configured — set SUBSCRIBERS in .env")
        return

    html = render_digest(summaries)
    subject = f"⚽ World Cup 2026 Tickets — Daily Digest {datetime.utcnow().strftime('%b %d')}"

    sg = SendGridAPIClient(api_key)
    for recipient in subscribers:
        message = Mail(
            from_email=from_email,
            to_emails=recipient,
            subject=subject,
            html_content=html,
        )
        response = sg.send(message)
        print(f"[digest] Sent to {recipient} — status {response.status_code}")
