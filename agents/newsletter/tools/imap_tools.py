"""
IMAP Tools - Direct IMAP integration for reading newsletter emails.

Alternative to Composio Gmail - free, no external dependencies.

Usage:
    1. Create Gmail App Password (Security → 2-Step Verification → App Passwords)
    2. Set environment variables:
       NEWSLETTER_IMAP_EMAIL=your@gmail.com
       NEWSLETTER_IMAP_PASSWORD=xxxx-xxxx-xxxx-xxxx
    3. Create Gmail labels: "Newsletters", "Newsletters/Processed"
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from crewai.tools import tool
from pydantic import BaseModel, Field
import os

# IMAP library
try:
    from imap_tools import MailBox, AND, OR, MailMessageFlags
    IMAP_AVAILABLE = True
except ImportError:
    IMAP_AVAILABLE = False
    MailMessageFlags = None
    print("Warning: imap-tools not installed. Run: pip install imap-tools")


class EmailMessage(BaseModel):
    """Pydantic model for email messages."""

    uid: str = Field(..., description="Email unique identifier")
    subject: str = Field(default="", description="Email subject")
    from_email: str = Field(default="", description="Sender email address")
    from_name: str = Field(default="", description="Sender display name")
    date: datetime = Field(default_factory=datetime.now, description="Email date")
    html: str = Field(default="", description="HTML content")
    text: str = Field(default="", description="Plain text content")
    is_newsletter: bool = Field(default=False, description="Detected as newsletter")


class IMAPNewsletterReader:
    """
    Direct IMAP client for Gmail newsletter reading.

    Free alternative to Composio - same functionality without external dependencies.
    """

    def __init__(
        self,
        email: Optional[str] = None,
        app_password: Optional[str] = None,
        host: str = "imap.gmail.com"
    ):
        """
        Initialize IMAP reader.

        Args:
            email: Gmail address (or from NEWSLETTER_IMAP_EMAIL env)
            app_password: Gmail App Password (or from NEWSLETTER_IMAP_PASSWORD env)
            host: IMAP server host
        """
        if not IMAP_AVAILABLE:
            raise ImportError("imap-tools required. Run: pip install imap-tools")

        self.email = email or os.getenv("NEWSLETTER_IMAP_EMAIL")
        self.password = app_password or os.getenv("NEWSLETTER_IMAP_PASSWORD")
        self.host = host

        if not self.email or not self.password:
            raise ValueError(
                "IMAP credentials required. Set NEWSLETTER_IMAP_EMAIL and "
                "NEWSLETTER_IMAP_PASSWORD environment variables."
            )

    def _connect(self) -> MailBox:
        """Create and return authenticated mailbox connection."""
        mailbox = MailBox(self.host)
        mailbox.login(self.email, self.password)
        return mailbox

    def _detect_newsletter(self, msg) -> bool:
        """Detect if an email is likely a newsletter."""
        indicators = [
            "newsletter" in msg.subject.lower(),
            "digest" in msg.subject.lower(),
            "weekly" in msg.subject.lower(),
            "unsubscribe" in msg.text.lower() if msg.text else False,
            "list-unsubscribe" in str(msg.headers).lower(),
        ]
        return any(indicators)

    def fetch_newsletters(
        self,
        days_back: int = 7,
        folder: str = "Newsletters",
        max_results: int = 20,
        unread_only: bool = False
    ) -> List[EmailMessage]:
        """
        Fetch newsletters from a specific folder.

        Args:
            days_back: How many days back to search
            folder: Gmail label/folder to read from
            max_results: Maximum emails to return
            unread_only: Only fetch unread emails

        Returns:
            List of EmailMessage objects
        """
        emails = []
        since_date = datetime.now() - timedelta(days=days_back)

        with self._connect() as mailbox:
            try:
                mailbox.folder.set(folder)
            except Exception:
                # Folder doesn't exist, fall back to INBOX
                mailbox.folder.set("INBOX")

            # Build query
            criteria = AND(date_gte=since_date.date())
            if unread_only:
                criteria = AND(criteria, seen=False)

            for msg in mailbox.fetch(criteria, limit=max_results, reverse=True):
                email = EmailMessage(
                    uid=msg.uid,
                    subject=msg.subject or "",
                    from_email=msg.from_ or "",
                    from_name=msg.from_values.name if msg.from_values else "",
                    date=msg.date or datetime.now(),
                    html=msg.html or "",
                    text=msg.text or "",
                    is_newsletter=self._detect_newsletter(msg),
                )
                emails.append(email)

        return emails

    def fetch_senders_from_inbox(
        self,
        days_back: int = 30,
        max_results: int = 200,
        folder: str = "INBOX",
        newsletters_only: bool = True,
    ) -> Tuple[List[Dict], int]:
        """
        Scan inbox headers and return grouped sender list.

        Uses headers_only=True for speed — no body download.

        Args:
            days_back: How many days back to scan
            max_results: Maximum emails to scan
            folder: Gmail folder to scan
            newsletters_only: Only return senders detected as newsletters

        Returns:
            Tuple of (list of sender dicts, total emails scanned)
        """
        since_date = datetime.now() - timedelta(days=days_back)
        senders: Dict[str, Dict] = {}
        total_scanned = 0

        with self._connect() as mailbox:
            try:
                mailbox.folder.set(folder)
            except Exception:
                mailbox.folder.set("INBOX")

            criteria = AND(date_gte=since_date.date())

            for msg in mailbox.fetch(
                criteria,
                limit=max_results,
                reverse=True,
                headers_only=True,
                mark_seen=False,
            ):
                total_scanned += 1
                email_addr = msg.from_ or ""
                if not email_addr:
                    continue

                is_newsletter = self._detect_newsletter(msg)

                if email_addr in senders:
                    senders[email_addr]["email_count"] += 1
                    # Update if this message is newer
                    if msg.date and (
                        not senders[email_addr]["latest_date"]
                        or msg.date.isoformat() > senders[email_addr]["latest_date"]
                    ):
                        senders[email_addr]["latest_subject"] = msg.subject or ""
                        senders[email_addr]["latest_date"] = (
                            msg.date.isoformat() if msg.date else None
                        )
                    # Mark as newsletter if any message from sender is detected
                    if is_newsletter:
                        senders[email_addr]["is_newsletter"] = True
                else:
                    senders[email_addr] = {
                        "from_email": email_addr,
                        "from_name": msg.from_values.name if msg.from_values else "",
                        "email_count": 1,
                        "is_newsletter": is_newsletter,
                        "latest_subject": msg.subject or "",
                        "latest_date": msg.date.isoformat() if msg.date else None,
                    }

        result = list(senders.values())

        if newsletters_only:
            result = [s for s in result if s["is_newsletter"]]

        # Sort: newsletters first, then by count descending
        result.sort(key=lambda s: (-int(s["is_newsletter"]), -s["email_count"]))

        return result, total_scanned

    def fetch_by_senders(
        self,
        sender_emails: List[str],
        days_back: int = 7,
        max_per_sender: int = 5
    ) -> List[EmailMessage]:
        """
        Fetch emails from specific senders (e.g., competitor newsletters).

        Args:
            sender_emails: List of sender email addresses
            days_back: How many days back to search
            max_per_sender: Maximum emails per sender

        Returns:
            List of EmailMessage objects
        """
        emails = []
        since_date = datetime.now() - timedelta(days=days_back)

        with self._connect() as mailbox:
            mailbox.folder.set("INBOX")

            for sender in sender_emails:
                criteria = AND(
                    date_gte=since_date.date(),
                    from_=sender
                )

                for msg in mailbox.fetch(criteria, limit=max_per_sender, reverse=True):
                    email = EmailMessage(
                        uid=msg.uid,
                        subject=msg.subject or "",
                        from_email=msg.from_ or "",
                        from_name=msg.from_values.name if msg.from_values else "",
                        date=msg.date or datetime.now(),
                        html=msg.html or "",
                        text=msg.text or "",
                        is_newsletter=self._detect_newsletter(msg),
                    )
                    emails.append(email)

        return emails

    def archive_email(
        self,
        uid: str,
        archive_folder: str = "Newsletters/Processed",
        source_folder: str = "Newsletters"
    ) -> bool:
        """
        Archive an email after processing.

        Args:
            uid: Email unique identifier
            archive_folder: Destination folder
            source_folder: Source folder

        Returns:
            True if successful
        """
        with self._connect() as mailbox:
            try:
                mailbox.folder.set(source_folder)
            except Exception:
                mailbox.folder.set("INBOX")

            # Move to archive folder
            mailbox.move([uid], archive_folder)
            return True

    def mark_as_read(self, uid: str, folder: str = "Newsletters") -> bool:
        """
        Mark an email as read.

        Args:
            uid: Email unique identifier
            folder: Folder containing the email

        Returns:
            True if successful
        """
        with self._connect() as mailbox:
            try:
                mailbox.folder.set(folder)
            except Exception:
                mailbox.folder.set("INBOX")

            mailbox.flag([uid], MailMessageFlags.SEEN, True)
            return True

    def archive_multiple(
        self,
        uids: List[str],
        archive_folder: str = "Newsletters/Processed",
        source_folder: str = "Newsletters"
    ) -> int:
        """
        Archive multiple emails after processing.

        Args:
            uids: List of email unique identifiers
            archive_folder: Destination folder
            source_folder: Source folder

        Returns:
            Number of emails archived
        """
        if not uids:
            return 0

        with self._connect() as mailbox:
            try:
                mailbox.folder.set(source_folder)
            except Exception:
                mailbox.folder.set("INBOX")

            mailbox.move(uids, archive_folder)
            return len(uids)


# Singleton instance for tools
_reader_instance: Optional[IMAPNewsletterReader] = None


def _get_reader() -> IMAPNewsletterReader:
    """Get or create IMAP reader instance."""
    global _reader_instance
    if _reader_instance is None:
        _reader_instance = IMAPNewsletterReader()
    return _reader_instance


@tool
def read_recent_newsletters(days: int = 7, max_emails: int = 20) -> str:
    """
    Read recent newsletter emails via IMAP (free, no Composio required).

    Args:
        days: Number of days back to search
        max_emails: Maximum number of emails to return

    Returns:
        Summary of newsletter emails found with UIDs for archiving
    """
    try:
        reader = _get_reader()
        emails = reader.fetch_newsletters(days_back=days, max_results=max_emails)

        if not emails:
            return "No newsletter emails found in the specified timeframe."

        summaries = []
        for email in emails:
            content_preview = (email.text[:300] + "...") if email.text else "(HTML only)"
            summaries.append(
                f"- UID: {email.uid}\n"
                f"  From: {email.from_name} <{email.from_email}>\n"
                f"  Subject: {email.subject}\n"
                f"  Date: {email.date.strftime('%Y-%m-%d %H:%M')}\n"
                f"  Preview: {content_preview}"
            )

        return f"Found {len(emails)} newsletters:\n\n" + "\n\n".join(summaries)

    except ValueError as e:
        return f"Configuration error: {str(e)}"
    except Exception as e:
        return f"Error reading emails: {str(e)}"


@tool
def read_competitor_newsletters(sender_emails: str) -> str:
    """
    Read newsletters from specific competitor email addresses via IMAP.

    Args:
        sender_emails: Comma-separated list of email addresses

    Returns:
        Content from competitor newsletters with UIDs for archiving
    """
    try:
        reader = _get_reader()
        senders = [s.strip() for s in sender_emails.split(",")]
        emails = reader.fetch_by_senders(senders)

        if not emails:
            return f"No emails found from: {sender_emails}"

        results = []
        for email in emails:
            content = email.text[:500] if email.text else "(HTML content)"
            results.append(
                f"## From: {email.from_name} <{email.from_email}>\n"
                f"**UID:** {email.uid}\n"
                f"**Subject:** {email.subject}\n"
                f"**Date:** {email.date.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"{content}..."
            )

        return "\n\n---\n\n".join(results)

    except ValueError as e:
        return f"Configuration error: {str(e)}"
    except Exception as e:
        return f"Error reading emails: {str(e)}"


@tool
def archive_processed_newsletter(email_uid: str) -> str:
    """
    Archive a newsletter email after it has been processed.

    Moves the email from Newsletters to Newsletters/Processed folder.

    Args:
        email_uid: The UID of the email to archive

    Returns:
        Confirmation message
    """
    try:
        reader = _get_reader()
        success = reader.archive_email(email_uid)

        if success:
            return f"Successfully archived email {email_uid}"
        else:
            return f"Failed to archive email {email_uid}"

    except ValueError as e:
        return f"Configuration error: {str(e)}"
    except Exception as e:
        return f"Error archiving email: {str(e)}"


@tool
def archive_multiple_newsletters(email_uids: str) -> str:
    """
    Archive multiple newsletter emails after processing.

    Args:
        email_uids: Comma-separated list of email UIDs to archive

    Returns:
        Confirmation message with count
    """
    try:
        reader = _get_reader()
        uids = [uid.strip() for uid in email_uids.split(",") if uid.strip()]
        count = reader.archive_multiple(uids)

        return f"Successfully archived {count} emails"

    except ValueError as e:
        return f"Configuration error: {str(e)}"
    except Exception as e:
        return f"Error archiving emails: {str(e)}"
