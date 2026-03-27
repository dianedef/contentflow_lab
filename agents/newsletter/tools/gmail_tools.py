"""
Gmail Tools - Composio integration for reading and sending emails.

Usage:
    1. Authenticate: `composio add gmail`
    2. Use tools in CrewAI agents

Actions available:
    - GMAIL_FETCH_EMAILS: Read emails from inbox
    - GMAIL_GET_EMAIL: Get specific email by ID
    - GMAIL_CREATE_EMAIL_DRAFT: Create draft for review
    - GMAIL_SEND_EMAIL: Send email directly
    - GMAIL_SEARCH_EMAILS: Search with Gmail query syntax
"""

from typing import List, Optional, Dict, Any
from crewai.tools import tool
import os

# Composio integration
try:
    from composio_crewai import ComposioToolSet, Action
    COMPOSIO_AVAILABLE = True
except ImportError:
    COMPOSIO_AVAILABLE = False
    print("Warning: composio-crewai not installed. Run: pip install composio-crewai")


def get_gmail_tools() -> List:
    """
    Get Gmail tools for CrewAI agents via Composio.

    Returns:
        List of CrewAI-compatible tools for Gmail operations
    """
    if not COMPOSIO_AVAILABLE:
        return []

    toolset = ComposioToolSet()

    return toolset.get_tools(
        actions=[
            Action.GMAIL_FETCH_EMAILS,
            Action.GMAIL_GET_EMAIL,
            Action.GMAIL_CREATE_EMAIL_DRAFT,
            Action.GMAIL_SEND_EMAIL,
            Action.GMAIL_SEARCH_EMAILS,
        ]
    )


class GmailReader:
    """
    High-level Gmail reader for newsletter curation.
    Wraps Composio tools with business logic.
    """

    def __init__(self):
        if not COMPOSIO_AVAILABLE:
            raise ImportError("composio-crewai required. Run: pip install composio-crewai")
        self.toolset = ComposioToolSet()

    def fetch_newsletter_emails(
        self,
        labels: Optional[List[str]] = None,
        max_results: int = 20,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails that look like newsletters.

        Args:
            labels: Gmail labels to filter (e.g., ["Newsletter", "Updates"])
            max_results: Maximum emails to return
            days_back: How many days back to search

        Returns:
            List of email dictionaries with subject, from, body, date
        """
        # Build Gmail search query
        query_parts = []

        if labels:
            label_query = " OR ".join([f"label:{label}" for label in labels])
            query_parts.append(f"({label_query})")

        # Common newsletter patterns
        query_parts.append("(subject:newsletter OR subject:digest OR subject:weekly OR subject:update)")
        query_parts.append(f"newer_than:{days_back}d")

        query = " ".join(query_parts)

        # Execute via Composio
        result = self.toolset.execute_action(
            action=Action.GMAIL_SEARCH_EMAILS,
            params={"query": query, "max_results": max_results}
        )

        return result.get("emails", [])

    def fetch_by_sender(
        self,
        sender_emails: List[str],
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from specific senders (e.g., competitor newsletters).

        Args:
            sender_emails: List of sender email addresses
            max_results: Maximum emails per sender

        Returns:
            List of email dictionaries
        """
        all_emails = []

        for sender in sender_emails:
            result = self.toolset.execute_action(
                action=Action.GMAIL_SEARCH_EMAILS,
                params={"query": f"from:{sender}", "max_results": max_results}
            )
            all_emails.extend(result.get("emails", []))

        return all_emails

    def get_email_content(self, email_id: str) -> Dict[str, Any]:
        """
        Get full email content by ID.

        Args:
            email_id: Gmail message ID

        Returns:
            Full email content including body
        """
        result = self.toolset.execute_action(
            action=Action.GMAIL_GET_EMAIL,
            params={"message_id": email_id}
        )
        return result


@tool
def read_recent_newsletters(days: int = 7, max_emails: int = 20) -> str:
    """
    Read recent newsletter emails from Gmail inbox.

    Args:
        days: Number of days back to search
        max_emails: Maximum number of emails to return

    Returns:
        Summary of newsletter emails found
    """
    try:
        reader = GmailReader()
        emails = reader.fetch_newsletter_emails(days_back=days, max_results=max_emails)

        if not emails:
            return "No newsletter emails found in the specified timeframe."

        summaries = []
        for email in emails:
            summaries.append(
                f"- From: {email.get('from', 'Unknown')}\n"
                f"  Subject: {email.get('subject', 'No subject')}\n"
                f"  Date: {email.get('date', 'Unknown date')}"
            )

        return f"Found {len(emails)} newsletters:\n\n" + "\n\n".join(summaries)

    except Exception as e:
        return f"Error reading emails: {str(e)}. Ensure Gmail is authenticated via: composio add gmail"


@tool
def read_competitor_newsletters(sender_emails: str) -> str:
    """
    Read newsletters from specific competitor email addresses.

    Args:
        sender_emails: Comma-separated list of email addresses

    Returns:
        Content from competitor newsletters
    """
    try:
        reader = GmailReader()
        senders = [s.strip() for s in sender_emails.split(",")]
        emails = reader.fetch_by_sender(senders)

        if not emails:
            return f"No emails found from: {sender_emails}"

        results = []
        for email in emails:
            results.append(
                f"## From: {email.get('from', 'Unknown')}\n"
                f"**Subject:** {email.get('subject', 'No subject')}\n"
                f"**Date:** {email.get('date', 'Unknown')}\n\n"
                f"{email.get('snippet', email.get('body', 'No content'))[:500]}..."
            )

        return "\n\n---\n\n".join(results)

    except Exception as e:
        return f"Error: {str(e)}"
