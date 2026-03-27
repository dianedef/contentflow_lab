# TASK: Newsletter Sending Pipeline

> **Robot**: Newsletter Robot
> **Tools**: Paced Email (sending)
> **Priority**: High

## Objective

Implement automated newsletter delivery using Paced Email API, integrated with the existing PydanticAI newsletter generation workflow.

---

## Implementation Checklist

### Phase 1: Paced Email Setup

- [ ] **Account & Configuration**
  - [ ] Create Paced Email account
  - [ ] Verify sending domain (DNS records)
  - [ ] Add `PACED_EMAIL_API_KEY` to `.env`
  - [ ] Add `NEWSLETTER_FROM_EMAIL` to `.env`

- [ ] **Email Client Module**
  - [ ] Create `src/newsletter/email_client.py`
  - [ ] Implement send function with retry logic
  - [ ] Add rate limiting (respect API limits)

```python
# src/newsletter/email_client.py
import requests
import os
from typing import Optional
import time

class PacedEmailClient:
    BASE_URL = "https://api.paced.email/v1"

    def __init__(self):
        self.api_key = os.getenv("PACED_EMAIL_API_KEY")
        self.from_email = os.getenv("NEWSLETTER_FROM_EMAIL")

    def send(
        self,
        to: str,
        subject: str,
        html: str,
        tags: Optional[list[str]] = None
    ) -> dict:
        """Send a single email."""
        response = requests.post(
            f"{self.BASE_URL}/send",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "to": to,
                "from": self.from_email,
                "subject": subject,
                "html": html,
                "tags": tags or ["newsletter"]
            }
        )
        response.raise_for_status()
        return response.json()

    def send_batch(
        self,
        recipients: list[str],
        subject: str,
        html: str,
        delay_ms: int = 100
    ) -> dict:
        """Send to multiple recipients with rate limiting."""
        results = {"success": [], "failed": []}

        for email in recipients:
            try:
                self.send(email, subject, html)
                results["success"].append(email)
            except Exception as e:
                results["failed"].append({"email": email, "error": str(e)})
            time.sleep(delay_ms / 1000)

        return results
```

### Phase 2: Template System

- [ ] **HTML Templates**
  - [ ] Create base newsletter template
  - [ ] Add responsive CSS (inline)
  - [ ] Support variable substitution

- [ ] **Template Management via API**
  - [ ] Create template upload function
  - [ ] Implement template-based sending

```python
# src/newsletter/templates.py
NEWSLETTER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
    .header { border-bottom: 2px solid #333; padding-bottom: 10px; }
    .section { margin: 20px 0; }
    .footer { font-size: 12px; color: #666; margin-top: 30px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{{title}}</h1>
      <p>{{subtitle}}</p>
    </div>
    <div class="content">
      {{content}}
    </div>
    <div class="footer">
      <p>{{footer_text}}</p>
      <p><a href="{{unsubscribe_url}}">Se désabonner</a></p>
    </div>
  </div>
</body>
</html>
"""

def render_newsletter(data: dict) -> str:
    """Render newsletter template with data."""
    html = NEWSLETTER_TEMPLATE
    for key, value in data.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))
    return html
```

### Phase 3: Integration with Newsletter Agent

- [ ] **Pipeline Connection**
  - [ ] Add email sending step to newsletter workflow
  - [ ] Connect Pydantic-validated content to templates
  - [ ] Implement send confirmation logging

```python
# src/newsletter/agents/newsletter_agent.py (addition)
from src.newsletter.email_client import PacedEmailClient
from src.newsletter.templates import render_newsletter

async def send_newsletter(newsletter_data: NewsletterSchema, recipients: list[str]):
    """Send generated newsletter to subscribers."""
    client = PacedEmailClient()

    html_content = render_newsletter({
        "title": newsletter_data.title,
        "subtitle": newsletter_data.subtitle,
        "content": newsletter_data.rendered_html,
        "footer_text": "Merci de votre lecture!",
        "unsubscribe_url": "https://example.com/unsubscribe"
    })

    results = client.send_batch(
        recipients=recipients,
        subject=newsletter_data.subject_line,
        html=html_content
    )

    return results
```

### Phase 4: Subscriber Management

- [ ] **Subscriber Storage**
  - [ ] Define subscriber schema
  - [ ] Implement add/remove functions
  - [ ] Support segmentation tags

- [ ] **Compliance**
  - [ ] Unsubscribe link in all emails
  - [ ] Double opt-in flow (optional)
  - [ ] GDPR-compliant data handling

---

## Process Flow

```
1. Newsletter Generation (existing PydanticAI workflow)
   └── Exa AI collects content
   └── Agent curates and structures
   └── Pydantic validates output

2. Template Rendering
   └── Load newsletter template
   └── Inject validated content
   └── Generate final HTML

3. Delivery (Paced Email)
   └── Fetch subscriber list
   └── Send batch with rate limiting
   └── Log delivery status

4. Post-Send
   └── Track opens/clicks (via Paced dashboard)
   └── Process bounces
   └── Update subscriber list
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Delivery rate | > 99% |
| Send latency | < 2s/email |
| Template render time | < 100ms |
| Bounce rate | < 2% |
| Cost per 1000 emails | ~$1 |

---

## Environment Variables

```bash
# .env
PACED_EMAIL_API_KEY=your_api_key_here
NEWSLETTER_FROM_EMAIL=newsletter@yourdomain.com
```

---

## Dependencies

- `requests` - HTTP client
- Existing `NewsletterSchema` from `src/schemas/newsletter_schema.py`
- Subscriber database (TBD: JSON file, SQLite, or external)

---

## Notes

- Test with small batch before full send
- Monitor Paced Email dashboard for deliverability issues
- Consider Encharge.io for advanced automation later
