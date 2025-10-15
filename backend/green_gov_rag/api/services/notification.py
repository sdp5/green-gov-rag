"""Notification service for document monitoring alerts.

Supports email notifications for:
- Document updates detected
- New documents discovered
- Monitoring failures
- Citation verification warnings
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuration for notification service."""

    # Email settings
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    from_email: str = "noreply@green-gov-rag.local"
    from_name: str = "Green Gov RAG Monitoring"

    # Notification preferences
    enabled: bool = True
    recipient_emails: list[str] | None = None
    notify_on_update: bool = True
    notify_on_discovery: bool = True
    notify_on_failure: bool = True
    notify_on_citation_warning: bool = False

    # Throttling
    min_notification_interval_seconds: int = 3600  # 1 hour


@dataclass
class DocumentUpdateNotification:
    """Notification payload for document updates."""

    document_id: str
    document_title: str
    source_url: str
    old_version: int
    new_version: int
    change_summary: str | None
    confidence_score: float
    discovered_at: datetime


@dataclass
class CitationWarningNotification:
    """Notification payload for citation warnings."""

    document_id: str
    document_title: str
    warning_type: str  # 'superseded', 'stale', 'quote_mismatch'
    warning_message: str
    cited_version: int | None
    current_version: int
    details: dict[str, Any] | None = None


class NotificationService:
    """Service for sending monitoring notifications.

    Supports:
    - Email notifications via SMTP
    - Document update alerts
    - Citation verification warnings
    - Monitoring failure alerts
    """

    def __init__(self, config: NotificationConfig | None = None):
        """Initialize notification service.

        Args:
            config: Notification configuration
        """
        self.config = config or NotificationConfig()
        self._last_notification_time: dict[str, datetime] = {}

    async def send_document_update_notification(
        self, update: DocumentUpdateNotification
    ) -> bool:
        """Send notification about document update.

        Args:
            update: Document update notification payload

        Returns:
            True if notification sent successfully
        """
        if not self.config.enabled or not self.config.notify_on_update:
            logger.debug("Document update notifications disabled")
            return False

        # Check throttling
        if not self._should_send_notification(f"update_{update.document_id}"):
            logger.debug(
                f"Skipping notification for {update.document_id} due to throttling"
            )
            return False

        subject = f"Document Updated: {update.document_title}"

        body = f"""
A document you're monitoring has been updated:

Document: {update.document_title}
Source: {update.source_url}

Version Change: v{update.old_version} → v{update.new_version}
Discovered: {update.discovered_at.strftime('%Y-%m-%d %H:%M UTC')}
Confidence: {update.confidence_score:.0%}

{f'Summary: {update.change_summary}' if update.change_summary else ''}

---
This is an automated notification from Green Gov RAG Document Monitoring.
        """.strip()

        return await self._send_email(
            subject=subject,
            body=body,
            recipients=self.config.recipient_emails,
        )

    async def send_new_document_notification(
        self, document_id: str, document_title: str, source_url: str
    ) -> bool:
        """Send notification about newly discovered document.

        Args:
            document_id: Document identifier
            document_title: Document title
            source_url: Source URL

        Returns:
            True if notification sent successfully
        """
        if not self.config.enabled or not self.config.notify_on_discovery:
            return False

        if not self._should_send_notification(f"new_{document_id}"):
            return False

        subject = f"New Document Discovered: {document_title}"

        body = f"""
A new document has been discovered:

Document: {document_title}
Source: {source_url}
Discovered: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

This document has been added to the monitoring system.

---
This is an automated notification from Green Gov RAG Document Monitoring.
        """.strip()

        return await self._send_email(
            subject=subject, body=body, recipients=self.config.recipient_emails
        )

    async def send_monitoring_failure_notification(
        self, source_type: str, error_message: str, run_id: str
    ) -> bool:
        """Send notification about monitoring failure.

        Args:
            source_type: Source type that failed
            error_message: Error message
            run_id: Monitoring run ID

        Returns:
            True if notification sent successfully
        """
        if not self.config.enabled or not self.config.notify_on_failure:
            return False

        if not self._should_send_notification(f"failure_{source_type}"):
            return False

        subject = f"Monitoring Failure: {source_type}"

        body = f"""
Document monitoring failed for source: {source_type}

Run ID: {run_id}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Error:
{error_message}

Please check the monitoring logs for details.

---
This is an automated notification from Green Gov RAG Document Monitoring.
        """.strip()

        return await self._send_email(
            subject=subject, body=body, recipients=self.config.recipient_emails
        )

    async def send_citation_warning_notification(
        self, warning: CitationWarningNotification
    ) -> bool:
        """Send notification about citation verification warning.

        Args:
            warning: Citation warning payload

        Returns:
            True if notification sent successfully
        """
        if not self.config.enabled or not self.config.notify_on_citation_warning:
            return False

        if not self._should_send_notification(f"citation_{warning.document_id}"):
            return False

        subject = f"Citation Warning: {warning.document_title}"

        warning_type_text = {
            "superseded": "Document version has been superseded",
            "stale": "Document may be outdated",
            "quote_mismatch": "Quote verification failed",
        }.get(warning.warning_type, "Citation issue detected")

        body = f"""
Citation verification warning:

Document: {warning.document_title}
Warning Type: {warning_type_text}

{warning.warning_message}

{f'Cited Version: v{warning.cited_version}' if warning.cited_version else ''}
Current Version: v{warning.current_version}

{self._format_details(warning.details) if warning.details else ''}

Action Required: Review citations referencing this document.

---
This is an automated notification from Green Gov RAG Document Monitoring.
        """.strip()

        return await self._send_email(
            subject=subject, body=body, recipients=self.config.recipient_emails
        )

    async def send_batch_update_summary(
        self, summary: dict[str, Any], period: str = "daily"
    ) -> bool:
        """Send summary email of all monitoring activity.

        Args:
            summary: Summary statistics dict
            period: Reporting period ('daily', 'weekly')

        Returns:
            True if notification sent successfully
        """
        if not self.config.enabled:
            return False

        subject = f"Monitoring Summary - {period.capitalize()}"

        body = f"""
Document Monitoring Summary ({period}):

Sources Monitored: {summary.get('sources_checked', 0)}
Documents Checked: {summary.get('documents_checked', 0)}

Updates Detected: {summary.get('documents_updated', 0)}
New Documents: {summary.get('documents_discovered', 0)}
Unchanged: {summary.get('documents_unchanged', 0)}

Failures: {summary.get('sources_failed', 0)}

{self._format_details(summary.get('details')) if summary.get('details') else ''}

---
This is an automated notification from Green Gov RAG Document Monitoring.
        """.strip()

        return await self._send_email(
            subject=subject, body=body, recipients=self.config.recipient_emails
        )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _should_send_notification(self, notification_key: str) -> bool:
        """Check if notification should be sent based on throttling.

        Args:
            notification_key: Key for throttling check

        Returns:
            True if notification should be sent
        """
        now = datetime.utcnow()
        last_sent = self._last_notification_time.get(notification_key)

        if not last_sent:
            self._last_notification_time[notification_key] = now
            return True

        elapsed_seconds = (now - last_sent).total_seconds()
        if elapsed_seconds >= self.config.min_notification_interval_seconds:
            self._last_notification_time[notification_key] = now
            return True

        return False

    async def _send_email(
        self,
        subject: str,
        body: str,
        recipients: list[str] | None = None,
    ) -> bool:
        """Send email notification.

        Args:
            subject: Email subject
            body: Email body (plain text)
            recipients: List of recipient emails

        Returns:
            True if email sent successfully
        """
        if not recipients:
            logger.warning("No recipient emails configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
            msg["To"] = ", ".join(recipients)

            # Add plain text body
            msg.attach(MIMEText(body, "plain"))

            # Connect to SMTP server
            if self.config.smtp_use_tls:
                smtp = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                smtp.starttls()
            else:
                smtp = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)

            # Login if credentials provided
            if self.config.smtp_username and self.config.smtp_password:
                smtp.login(self.config.smtp_username, self.config.smtp_password)

            # Send email
            smtp.sendmail(self.config.from_email, recipients, msg.as_string())
            smtp.quit()

            logger.info(f"Email sent: {subject} to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False

    def _format_details(self, details: dict[str, Any] | None) -> str:
        """Format details dict for email body.

        Args:
            details: Details dictionary

        Returns:
            Formatted string
        """
        if not details:
            return ""

        lines = ["Details:"]
        for key, value in details.items():
            lines.append(f"  {key}: {value}")

        return "\n".join(lines)


# ============================================================================
# Configuration Helper
# ============================================================================


def create_notification_config_from_settings(settings: Any) -> NotificationConfig:
    """Create NotificationConfig from app settings.

    Args:
        settings: Application settings object

    Returns:
        NotificationConfig instance
    """
    return NotificationConfig(
        smtp_host=getattr(settings, "smtp_host", "localhost"),
        smtp_port=getattr(settings, "smtp_port", 587),
        smtp_username=getattr(settings, "smtp_username", None),
        smtp_password=getattr(settings, "smtp_password", None),
        smtp_use_tls=getattr(settings, "smtp_use_tls", True),
        from_email=getattr(
            settings, "notification_from_email", "noreply@green-gov-rag.local"
        ),
        from_name=getattr(settings, "notification_from_name", "Green Gov RAG"),
        enabled=getattr(settings, "enable_notifications", False),
        recipient_emails=getattr(settings, "notification_recipients", []),
        notify_on_update=getattr(settings, "notify_on_update", True),
        notify_on_discovery=getattr(settings, "notify_on_discovery", True),
        notify_on_failure=getattr(settings, "notify_on_failure", True),
        notify_on_citation_warning=getattr(
            settings, "notify_on_citation_warning", False
        ),
        min_notification_interval_seconds=getattr(
            settings, "notification_throttle_seconds", 3600
        ),
    )
