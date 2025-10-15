# Document Update Pipeline & Citation Verification - Implementation Plan

## Executive Summary

After comprehensive codebase analysis, GreenGovRAG currently has **solid foundations** but **lacks automated monitoring and citation verification** required for production regulatory compliance systems.

**Current State**: 60% Complete
- ✅ ETL pipeline with source registry
- ✅ Document metadata models
- ✅ Citation metadata schema (recently added)
- ✅ Vector store infrastructure
- ❌ **No automated monitoring/crawling**
- ❌ **No version tracking/change detection**
- ❌ **No citation verification system**
- ❌ **No scheduling infrastructure (Celery/Airflow)**

---

## Part 1: Document Update Pipeline (Automated Monitoring)

### Current Implementation Assessment

#### ✅ What Exists:
1. **Document Source Registry** (`etl/sources/registry.py`)
   - Plugin-based architecture for different source types
   - Can register federal, state, local, emissions sources
   - Factory pattern for creating sources

2. **ETL Pipeline** (`etl/pipeline.py`)
   - Enhanced pipeline with metadata tagging
   - Cloud storage support (S3/Azure)
   - Chunking with metadata preservation

3. **Document Model** (`models/document.py`)
   - Basic metadata: title, source_url, jurisdiction, topic
   - Processing status: pending/processing/completed/failed
   - Timestamps: created_at, updated_at, processed_at
   - Chunk count and embedding model tracking

4. **Document Configuration** (`configs/documents_config.yml`)
   - YAML-based document registry
   - Metadata for 50+ Australian government documents
   - Download URLs, ESG metadata, spatial metadata

#### ❌ What's Missing:

**1. No Automated Crawling/Monitoring**
- Currently: Manual addition to documents_config.yml
- Need: Automated web scrapers for government websites

**2. No Change Detection**
- Currently: No checksums, hashes, or version comparison
- Need: Detect when PDFs are updated on source websites

**3. No Version Tracking**
- Currently: Document model has no version field
- Need: Track document versions, effective dates, superseded docs

**4. No Scheduling Infrastructure**
- Currently: No Celery, APScheduler, or Airflow integration
- Need: Daily/weekly scheduled monitoring tasks

**5. No Notification System**
- Currently: No alerts for new documents or updates
- Need: Admin notifications when updates detected

### Implementation Plan

#### Phase 1: Foundation (Week 1-2) - 5-7 days

**1.1 Enhance Document Model with Versioning**

File: `green_gov_rag/models/document.py`

```python
from sqlmodel import Field, SQLModel
from datetime import datetime, date

class DocumentVersion(SQLModel, table=True):
    """Track document versions over time."""

    __tablename__ = "document_versions"

    id: str = Field(primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    version: str = Field(description="Version number (e.g., '2.1', '2024-v3')")

    # Version metadata
    effective_date: date | None = Field(None, description="When this version takes effect")
    published_date: date | None = Field(None, description="When published")
    supersedes_version: str | None = Field(None, description="Previous version ID")

    # Change detection
    content_hash: str = Field(description="SHA256 hash of content")
    file_size: int = Field(description="File size in bytes")
    last_modified: datetime = Field(description="Last modified timestamp from source")

    # Source tracking
    source_url: str = Field(description="Download URL for this version")
    download_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Status
    status: str = Field(default="current", description="current/superseded/deprecated")
    change_notes: str | None = Field(None, description="What changed in this version")

class Document(SQLModel, table=True):
    """Enhanced with version tracking."""

    # ... existing fields ...

    # NEW: Version tracking
    current_version: str | None = Field(None, description="Current version ID")
    version_history: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # NEW: Change detection
    content_hash: str | None = Field(None, description="Current content hash")
    last_checked: datetime | None = Field(None, description="Last monitoring check")
    check_frequency: str = Field(default="daily", description="daily/weekly/monthly")

    # NEW: Monitoring flags
    auto_update: bool = Field(default=True, description="Auto-download updates")
    monitor_enabled: bool = Field(default=True, description="Enable monitoring")
```

**1.2 Create Document Monitor Base Class**

File: `green_gov_rag/monitoring/base_monitor.py`

```python
"""Base interface for document monitoring."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ChangeDetectionResult:
    """Result of change detection check."""

    has_changed: bool
    current_hash: str
    previous_hash: str | None
    current_size: int
    previous_size: int | None
    last_modified: datetime | None
    change_type: str | None  # "content", "metadata", "new"
    details: dict[str, Any]


@dataclass
class MonitoringResult:
    """Result of monitoring check for a document source."""

    source_url: str
    check_timestamp: datetime
    is_available: bool
    has_updates: bool
    new_documents: list[str]
    updated_documents: list[dict]
    errors: list[str]
    warnings: list[str]


class DocumentMonitor(ABC):
    """Base class for document source monitors.

    Each government website/API should have a specific monitor implementation.
    """

    @abstractmethod
    async def check_for_updates(self, source_config: dict) -> MonitoringResult:
        """Check source for new or updated documents.

        Args:
            source_config: Configuration for this source (URL, params, etc.)

        Returns:
            MonitoringResult with findings
        """
        pass

    @abstractmethod
    async def download_document(self, url: str, version_info: dict) -> bytes:
        """Download a document from the source.

        Args:
            url: Document URL
            version_info: Version metadata

        Returns:
            Document content as bytes
        """
        pass

    @abstractmethod
    def detect_changes(
        self,
        current_content: bytes,
        previous_hash: str | None,
        metadata: dict
    ) -> ChangeDetectionResult:
        """Detect if document has changed.

        Args:
            current_content: Current document content
            previous_hash: Previous content hash
            metadata: Document metadata

        Returns:
            ChangeDetectionResult
        """
        pass

    def compute_hash(self, content: bytes) -> str:
        """Compute SHA256 hash of content."""
        import hashlib
        return hashlib.sha256(content).hexdigest()
```

**1.3 Create Website-Specific Monitors**

File: `green_gov_rag/monitoring/monitors/cer_monitor.py`

```python
"""Monitor for Clean Energy Regulator (CER) website."""

import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from green_gov_rag.monitoring.base_monitor import DocumentMonitor, MonitoringResult, ChangeDetectionResult


class CERMonitor(DocumentMonitor):
    """Monitor Clean Energy Regulator publications.

    Monitors: https://cer.gov.au/schemes/nger/resources/measurement-guidelines
    """

    BASE_URL = "https://www.cleanenergyregulator.gov.au"
    GUIDELINES_URL = f"{BASE_URL}/NGER/About-the-National-Greenhouse-and-Energy-Reporting-scheme/Measurement-guidelines"

    async def check_for_updates(self, source_config: dict) -> MonitoringResult:
        """Scrape CER website for updated guidelines."""

        result = MonitoringResult(
            source_url=self.GUIDELINES_URL,
            check_timestamp=datetime.utcnow(),
            is_available=True,
            has_updates=False,
            new_documents=[],
            updated_documents=[],
            errors=[],
            warnings=[]
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.GUIDELINES_URL) as response:
                    if response.status != 200:
                        result.is_available = False
                        result.errors.append(f"HTTP {response.status}")
                        return result

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Find all PDF links in guidelines section
                    pdf_links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf'))

                    for link in pdf_links:
                        pdf_url = link.get('href')
                        if not pdf_url.startswith('http'):
                            pdf_url = self.BASE_URL + pdf_url

                        title = link.get_text(strip=True)

                        # Check if this is a known document
                        doc_info = {
                            "url": pdf_url,
                            "title": title,
                            "discovered_at": datetime.utcnow().isoformat()
                        }

                        # This would check against database
                        # For now, add to new_documents
                        result.new_documents.append(pdf_url)
                        result.has_updates = True

        except Exception as e:
            result.errors.append(str(e))
            result.is_available = False

        return result

    async def download_document(self, url: str, version_info: dict) -> bytes:
        """Download PDF from CER website."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()

    def detect_changes(
        self,
        current_content: bytes,
        previous_hash: str | None,
        metadata: dict
    ) -> ChangeDetectionResult:
        """Detect changes in CER document."""

        current_hash = self.compute_hash(current_content)
        current_size = len(current_content)

        has_changed = previous_hash is None or current_hash != previous_hash

        change_type = None
        if previous_hash is None:
            change_type = "new"
        elif has_changed:
            change_type = "content"

        return ChangeDetectionResult(
            has_changed=has_changed,
            current_hash=current_hash,
            previous_hash=previous_hash,
            current_size=current_size,
            previous_size=metadata.get("file_size"),
            last_modified=datetime.utcnow(),
            change_type=change_type,
            details={"source": "CER", "method": "web_scraping"}
        )
```

File: `green_gov_rag/monitoring/monitors/legislation_au_monitor.py`

```python
"""Monitor for legislation.gov.au (federal legislation)."""

import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime
from green_gov_rag.monitoring.base_monitor import DocumentMonitor, MonitoringResult


class LegislationAUMonitor(DocumentMonitor):
    """Monitor legislation.gov.au for federal acts and regulations.

    Uses legislation.gov.au API/RSS feeds where available.
    """

    BASE_URL = "https://www.legislation.gov.au"
    RSS_FEED = f"{BASE_URL}/rss/latest-updates"

    async def check_for_updates(self, source_config: dict) -> MonitoringResult:
        """Check RSS feed for legislative updates."""

        result = MonitoringResult(
            source_url=self.RSS_FEED,
            check_timestamp=datetime.utcnow(),
            is_available=True,
            has_updates=False,
            new_documents=[],
            updated_documents=[],
            errors=[],
            warnings=[]
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.RSS_FEED) as response:
                    if response.status != 200:
                        result.is_available = False
                        result.errors.append(f"HTTP {response.status}")
                        return result

                    xml_content = await response.text()
                    root = ET.fromstring(xml_content)

                    # Parse RSS items
                    for item in root.findall('.//item'):
                        title = item.find('title').text
                        link = item.find('link').text
                        pub_date = item.find('pubDate').text

                        # Check if this is environmental/climate related
                        if any(keyword in title.lower() for keyword in
                               ['environment', 'climate', 'emissions', 'energy']):
                            result.new_documents.append(link)
                            result.has_updates = True

        except Exception as e:
            result.errors.append(str(e))
            result.is_available = False

        return result

    # ... implement download_document and detect_changes ...
```

**1.4 Create Monitoring Service**

File: `green_gov_rag/monitoring/monitoring_service.py`

```python
"""Document monitoring service - orchestrates monitors and processes updates."""

import logging
from datetime import datetime
from typing import Any
from sqlmodel import Session, select

from green_gov_rag.models import Document, DocumentVersion
from green_gov_rag.models.base import engine
from green_gov_rag.monitoring.base_monitor import DocumentMonitor
from green_gov_rag.monitoring.monitor_registry import MonitorRegistry
from green_gov_rag.etl.pipeline import EnhancedETLPipeline

logger = logging.getLogger(__name__)


class DocumentMonitoringService:
    """Orchestrate document monitoring across all sources."""

    def __init__(self):
        self.monitor_registry = MonitorRegistry()
        self.etl_pipeline = EnhancedETLPipeline()

    async def monitor_all_sources(self) -> dict[str, Any]:
        """Check all registered sources for updates.

        Returns:
            Summary of monitoring run
        """
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "sources_checked": 0,
            "updates_found": 0,
            "new_documents": 0,
            "errors": [],
            "details": []
        }

        with Session(engine) as session:
            # Get all monitored documents
            stmt = select(Document).where(Document.monitor_enabled == True)
            documents = session.exec(stmt).all()

            for doc in documents:
                summary["sources_checked"] += 1

                try:
                    # Get appropriate monitor
                    monitor = self.monitor_registry.get_monitor_for_document(doc)

                    if monitor is None:
                        logger.warning(f"No monitor found for {doc.title}")
                        continue

                    # Check for updates
                    source_config = {
                        "url": doc.source_url,
                        "title": doc.title,
                        "jurisdiction": doc.jurisdiction
                    }

                    result = await monitor.check_for_updates(source_config)

                    if result.has_updates:
                        summary["updates_found"] += 1

                        # Process each update
                        for url in result.new_documents:
                            await self._process_new_document(url, doc, monitor)
                            summary["new_documents"] += 1

                        for update_info in result.updated_documents:
                            await self._process_document_update(update_info, doc, monitor)

                    # Update last_checked timestamp
                    doc.last_checked = datetime.utcnow()
                    session.add(doc)

                    summary["details"].append({
                        "document": doc.title,
                        "status": "checked",
                        "updates": result.has_updates
                    })

                except Exception as e:
                    logger.error(f"Error monitoring {doc.title}: {e}", exc_info=True)
                    summary["errors"].append({
                        "document": doc.title,
                        "error": str(e)
                    })

            session.commit()

        return summary

    async def _process_new_document(
        self,
        url: str,
        parent_doc: Document,
        monitor: DocumentMonitor
    ) -> None:
        """Process a newly discovered document."""
        logger.info(f"Processing new document: {url}")

        # Download document
        content = await monitor.download_document(url, {})

        # Compute hash
        content_hash = monitor.compute_hash(content)

        # Create new document version
        with Session(engine) as session:
            version = DocumentVersion(
                id=f"{parent_doc.id}_v{datetime.utcnow().strftime('%Y%m%d')}",
                document_id=parent_doc.id,
                version=datetime.utcnow().strftime('%Y-%m-%d'),
                source_url=url,
                content_hash=content_hash,
                file_size=len(content),
                last_modified=datetime.utcnow(),
                status="current"
            )

            session.add(version)

            # Update parent document
            parent_doc.current_version = version.id
            parent_doc.content_hash = content_hash
            session.add(parent_doc)

            session.commit()

        # Queue for ETL processing
        # This would trigger the ETL pipeline to process the new document
        # For now, log it
        logger.info(f"New version created: {version.id}")

    async def _process_document_update(
        self,
        update_info: dict,
        doc: Document,
        monitor: DocumentMonitor
    ) -> None:
        """Process an updated document."""
        logger.info(f"Processing update for: {doc.title}")

        # Similar to _process_new_document but marks old version as superseded
        # Implementation would download, check hash, create new version, etc.
        pass
```

**1.5 Create Scheduling Infrastructure**

File: `green_gov_rag/monitoring/scheduler.py`

```python
"""Scheduled monitoring tasks using APScheduler."""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from green_gov_rag.monitoring.monitoring_service import DocumentMonitoringService
from green_gov_rag.monitoring.notifications import NotificationService

logger = logging.getLogger(__name__)


class MonitoringScheduler:
    """Schedule automated document monitoring tasks."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.monitoring_service = DocumentMonitoringService()
        self.notification_service = NotificationService()

    def start(self):
        """Start the scheduler with configured jobs."""

        # Daily monitoring job - runs at 2 AM
        self.scheduler.add_job(
            self._run_daily_monitoring,
            trigger=CronTrigger(hour=2, minute=0),
            id="daily_monitoring",
            name="Daily Document Monitoring",
            replace_existing=True
        )

        # Weekly deep scan - runs Sunday at 3 AM
        self.scheduler.add_job(
            self._run_weekly_deep_scan,
            trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
            id="weekly_deep_scan",
            name="Weekly Deep Document Scan",
            replace_existing=True
        )

        # High-priority sources - every 6 hours
        self.scheduler.add_job(
            self._run_priority_monitoring,
            trigger=CronTrigger(hour='*/6'),
            id="priority_monitoring",
            name="Priority Source Monitoring",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Monitoring scheduler started")

    async def _run_daily_monitoring(self):
        """Daily monitoring task."""
        logger.info("Starting daily monitoring run")

        try:
            summary = await self.monitoring_service.monitor_all_sources()

            # Send notification if updates found
            if summary["updates_found"] > 0:
                await self.notification_service.notify_admins(
                    subject=f"Document Updates Detected ({summary['updates_found']})",
                    message=self._format_summary(summary)
                )

            logger.info(f"Daily monitoring complete: {summary}")

        except Exception as e:
            logger.error(f"Daily monitoring failed: {e}", exc_info=True)
            await self.notification_service.notify_error(
                "Daily Monitoring Failed",
                str(e)
            )

    async def _run_weekly_deep_scan(self):
        """Weekly deep scan of all sources."""
        logger.info("Starting weekly deep scan")
        # Implementation for thorough weekly check
        pass

    async def _run_priority_monitoring(self):
        """Monitor high-priority sources more frequently."""
        logger.info("Starting priority monitoring")
        # Implementation for critical sources (e.g., CER guidelines)
        pass

    def _format_summary(self, summary: dict) -> str:
        """Format monitoring summary for notification."""
        return f"""
Document Monitoring Summary - {summary['timestamp']}

Sources Checked: {summary['sources_checked']}
Updates Found: {summary['updates_found']}
New Documents: {summary['new_documents']}
Errors: {len(summary['errors'])}

Details:
{chr(10).join([f"- {d['document']}: {'Updated' if d['updates'] else 'No changes'}"
               for d in summary['details'][:10]])}
"""

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Monitoring scheduler stopped")


# FastAPI integration
async def start_monitoring_scheduler():
    """Start scheduler on application startup."""
    scheduler = MonitoringScheduler()
    scheduler.start()
    return scheduler

# Add to FastAPI app
# @app.on_event("startup")
# async def startup_event():
#     app.state.monitoring_scheduler = await start_monitoring_scheduler()
```

**1.6 Create Notification System**

File: `green_gov_rag/monitoring/notifications.py`

```python
"""Notification system for document monitoring alerts."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from green_gov_rag.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Send notifications to administrators."""

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.admin_emails = settings.admin_emails or []

    async def notify_admins(self, subject: str, message: str) -> None:
        """Send email notification to administrators.

        Args:
            subject: Email subject
            message: Email body
        """
        if not self.admin_emails:
            logger.warning("No admin emails configured")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = ', '.join(self.admin_emails)
            msg['Subject'] = f"[GreenGovRAG] {subject}"

            msg.attach(MIMEText(message, 'plain'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Notification sent: {subject}")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}", exc_info=True)

    async def notify_error(self, error_title: str, error_details: str) -> None:
        """Send error notification."""
        await self.notify_admins(
            subject=f"ERROR: {error_title}",
            message=f"""
An error occurred in the document monitoring system:

{error_title}

Details:
{error_details}

Please investigate immediately.
"""
        )

    async def notify_new_document(
        self,
        document_title: str,
        document_url: str,
        source: str
    ) -> None:
        """Notify about a newly discovered document."""
        await self.notify_admins(
            subject=f"New Document Discovered: {document_title}",
            message=f"""
A new government document has been detected:

Title: {document_title}
Source: {source}
URL: {document_url}

The document has been automatically downloaded and queued for processing.
"""
        )
```

#### Phase 2: Monitor Registry & Integration (Week 3) - 5-7 days

**2.1 Monitor Registry**

File: `green_gov_rag/monitoring/monitor_registry.py`

```python
"""Registry for document monitors - plugin architecture."""

from typing import Type, Dict
from green_gov_rag.monitoring.base_monitor import DocumentMonitor
from green_gov_rag.monitoring.monitors.cer_monitor import CERMonitor
from green_gov_rag.monitoring.monitors.legislation_au_monitor import LegislationAUMonitor


class MonitorRegistry:
    """Registry for document source monitors."""

    def __init__(self):
        self._monitors: Dict[str, Type[DocumentMonitor]] = {}
        self._register_default_monitors()

    def _register_default_monitors(self):
        """Register built-in monitors."""
        self.register("cer", CERMonitor)
        self.register("legislation_au", LegislationAUMonitor)
        # Add more monitors here

    def register(self, source_type: str, monitor_class: Type[DocumentMonitor]):
        """Register a monitor for a source type."""
        self._monitors[source_type] = monitor_class

    def get_monitor_for_document(self, document) -> DocumentMonitor | None:
        """Get appropriate monitor for a document."""

        # Determine source type from document metadata
        if "cleanenergyregulator.gov.au" in document.source_url:
            return CERMonitor()
        elif "legislation.gov.au" in document.source_url:
            return LegislationAUMonitor()

        return None
```

**2.2 CLI Commands**

File: `green_gov_rag/cli.py` (additions)

```python
@app.command()
def monitor(
    once: bool = typer.Option(False, help="Run once and exit"),
    sources: str = typer.Option(None, help="Comma-separated list of sources")
):
    """Start document monitoring service."""
    import asyncio
    from green_gov_rag.monitoring.monitoring_service import DocumentMonitoringService

    async def run():
        service = DocumentMonitoringService()
        summary = await service.monitor_all_sources()
        print(json.dumps(summary, indent=2))

    asyncio.run(run())

@app.command()
def start_scheduler():
    """Start the monitoring scheduler (runs in background)."""
    from green_gov_rag.monitoring.scheduler import MonitoringScheduler
    import asyncio

    scheduler = MonitoringScheduler()
    scheduler.start()

    print("Monitoring scheduler started. Press Ctrl+C to stop.")

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        scheduler.stop()
        print("\nScheduler stopped.")
```

#### Phase 3: Admin UI (Week 4) - 5-7 days

**3.1 Admin API Endpoints**

File: `green_gov_rag/api/admin/monitoring.py`

```python
"""Admin API endpoints for document monitoring."""

from fastapi import APIRouter, HTTPException
from green_gov_rag.monitoring.monitoring_service import DocumentMonitoringService

router = APIRouter(prefix="/admin/monitoring", tags=["admin", "monitoring"])

@router.get("/status")
async def get_monitoring_status():
    """Get current monitoring status."""
    # Return status of all monitors
    pass

@router.post("/run")
async def trigger_monitoring_run():
    """Manually trigger a monitoring run."""
    service = DocumentMonitoringService()
    summary = await service.monitor_all_sources()
    return summary

@router.get("/sources")
async def list_monitored_sources():
    """List all monitored document sources."""
    pass

@router.put("/sources/{document_id}/monitor")
async def enable_monitoring(document_id: str):
    """Enable monitoring for a specific document."""
    pass

@router.delete("/sources/{document_id}/monitor")
async def disable_monitoring(document_id: str):
    """Disable monitoring for a specific document."""
    pass

@router.get("/history")
async def get_monitoring_history(
    days: int = 7,
    document_id: str | None = None
):
    """Get monitoring history."""
    pass
```

### Priority Order

**Immediate (MVP - 2 weeks)**:
1. Document version model (1 day)
2. Base monitor interface (1 day)
3. CER monitor implementation (2 days)
4. Change detection (1 day)
5. Basic scheduling with APScheduler (2 days)
6. Email notifications (1 day)
7. CLI commands (1 day)
8. Testing (3 days)

**Post-MVP (Month 2)**:
9. Additional monitors (NSW EPA, VIC EPA, legislation.gov.au)
10. Admin UI
11. Monitoring dashboard
12. Advanced notification channels (Slack, webhooks)

---

## Part 2: Citation Verification System

### Current Implementation Assessment

#### ✅ What Exists:
1. **Citation Metadata Schema** (Just added!)
   - Enhanced `SourceDocument` schema with citation fields
   - Page numbers, section hierarchy, clause references
   - Deep linking, formatted citations
   - ESG and spatial metadata

2. **Citation Formatter** (`api/utils/citation_formatter.py`)
   - Formats citations from metadata
   - Builds deep links to PDFs
   - Generates professional citation strings

3. **Hierarchical PDF Parsing** (`etl/parsers/layout_parser.py`)
   - LLMSherpa LayoutPDFReader integration
   - Extracts section hierarchy
   - Preserves page boundaries

#### ❌ What's Missing:

**1. No Quote Verification**
- Currently: Citations link to pages/sections
- Need: Verify LLM output matches source text exactly

**2. No Version Currency Checking**
- Currently: No way to know if cited doc is current
- Need: Check if newer version exists, flag if superseded

**3. No Conflict Detection**
- Currently: No cross-document analysis
- Need: Detect conflicting regulations, show hierarchy

**4. No Confidence Scoring**
- Currently: No quality metrics on citations
- Need: Score citation accuracy and reliability

**5. No Audit Trail**
- Currently: No provenance tracking
- Need: Full chain from query → retrieval → generation → citation

### Implementation Plan

#### Phase 1: Quote Verification (Week 1) - 5-7 days

**1.1 Citation Verifier Base**

File: `green_gov_rag/verification/citation_verifier.py`

```python
"""Citation verification system for RAG responses."""

from dataclasses import dataclass
from typing import Any, List, Tuple
import difflib
from datetime import datetime

from langchain.docstore.document import Document
from sqlmodel import Session, select

from green_gov_rag.models import DocumentVersion
from green_gov_rag.models.base import engine


@dataclass
class VerificationResult:
    """Result of citation verification."""

    is_verified: bool
    confidence_score: float  # 0.0 - 1.0
    match_type: str  # "exact", "paraphrase", "inference", "not_found"

    # Quote matching
    claimed_text: str
    source_text: str | None
    similarity_score: float

    # Version checking
    is_current_version: bool
    version_info: dict
    superseded_by: str | None

    # Provenance
    source_document_id: str
    page_number: int | None
    section_reference: str | None

    # Warnings
    warnings: List[str]
    errors: List[str]


class CitationVerifier:
    """Verify citations in RAG responses."""

    def __init__(self, similarity_threshold: float = 0.85):
        """Initialize verifier.

        Args:
            similarity_threshold: Minimum similarity for "verified" status
        """
        self.similarity_threshold = similarity_threshold

    def verify_citation(
        self,
        claimed_text: str,
        source_document: dict,
        page_number: int | None = None,
        section_reference: str | None = None
    ) -> VerificationResult:
        """Verify a single citation claim.

        Args:
            claimed_text: Text claimed to be from source
            source_document: Source document metadata
            page_number: Claimed page number
            section_reference: Claimed section

        Returns:
            VerificationResult with verification details
        """
        warnings = []
        errors = []

        # Step 1: Load source document content
        source_text = self._load_source_content(
            source_document,
            page_number,
            section_reference
        )

        if source_text is None:
            return VerificationResult(
                is_verified=False,
                confidence_score=0.0,
                match_type="not_found",
                claimed_text=claimed_text,
                source_text=None,
                similarity_score=0.0,
                is_current_version=False,
                version_info={},
                superseded_by=None,
                source_document_id=source_document.get("id", "unknown"),
                page_number=page_number,
                section_reference=section_reference,
                warnings=[],
                errors=["Source text not found"]
            )

        # Step 2: Check for exact match
        if claimed_text.strip() in source_text:
            match_type = "exact"
            similarity_score = 1.0
        else:
            # Step 3: Calculate similarity
            similarity_score = self._calculate_similarity(claimed_text, source_text)

            if similarity_score >= self.similarity_threshold:
                match_type = "paraphrase"
            elif similarity_score >= 0.5:
                match_type = "inference"
                warnings.append(
                    f"Low similarity ({similarity_score:.2f}). "
                    "Claimed text may be inferred rather than quoted."
                )
            else:
                match_type = "not_found"
                errors.append(
                    f"Very low similarity ({similarity_score:.2f}). "
                    "Claimed text not found in source."
                )

        # Step 4: Check version currency
        version_info = self._check_version_currency(source_document)

        is_current = version_info.get("is_current", True)
        superseded_by = version_info.get("superseded_by")

        if not is_current:
            warnings.append(
                f"Document superseded by version {superseded_by}. "
                "Citation may be outdated."
            )

        # Step 5: Calculate confidence score
        confidence_score = self._calculate_confidence(
            similarity_score,
            match_type,
            is_current,
            len(warnings),
            len(errors)
        )

        is_verified = (
            match_type in ["exact", "paraphrase"] and
            confidence_score >= self.similarity_threshold and
            len(errors) == 0
        )

        return VerificationResult(
            is_verified=is_verified,
            confidence_score=confidence_score,
            match_type=match_type,
            claimed_text=claimed_text,
            source_text=source_text[:500],  # First 500 chars for context
            similarity_score=similarity_score,
            is_current_version=is_current,
            version_info=version_info,
            superseded_by=superseded_by,
            source_document_id=source_document.get("id", "unknown"),
            page_number=page_number,
            section_reference=section_reference,
            warnings=warnings,
            errors=errors
        )

    def verify_response(
        self,
        answer: str,
        sources: List[dict],
        extract_claims: bool = True
    ) -> List[VerificationResult]:
        """Verify all citations in a RAG response.

        Args:
            answer: LLM-generated answer
            sources: Source documents cited
            extract_claims: Whether to extract claims from answer

        Returns:
            List of VerificationResult for each claim/citation
        """
        results = []

        if extract_claims:
            # Extract claims from answer text
            claims = self._extract_claims(answer)

            for claim in claims:
                # Try to match claim to source
                best_match = self._find_best_source(claim, sources)

                if best_match:
                    result = self.verify_citation(
                        claimed_text=claim,
                        source_document=best_match
                    )
                    results.append(result)
        else:
            # Verify each source was accurately cited
            for source in sources:
                excerpt = source.get("excerpt", "")
                if excerpt:
                    result = self.verify_citation(
                        claimed_text=excerpt,
                        source_document=source,
                        page_number=source.get("page_number"),
                        section_reference=source.get("clause_reference")
                    )
                    results.append(result)

        return results

    def _load_source_content(
        self,
        source_document: dict,
        page_number: int | None,
        section_reference: str | None
    ) -> str | None:
        """Load source document content for verification."""
        # Implementation would load from vector store or document storage
        # For now, return None (to be implemented with actual storage)
        return None

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        # Use SequenceMatcher for simple similarity
        matcher = difflib.SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()

    def _check_version_currency(self, source_document: dict) -> dict:
        """Check if source document is the current version."""
        doc_id = source_document.get("id")

        if not doc_id:
            return {"is_current": True, "superseded_by": None}

        with Session(engine) as session:
            # Check for newer versions
            stmt = select(DocumentVersion).where(
                DocumentVersion.document_id == doc_id,
                DocumentVersion.status == "current"
            )
            current_version = session.exec(stmt).first()

            if current_version:
                # Check if this is the current version
                source_version_id = source_document.get("version_id")
                is_current = source_version_id == current_version.id

                return {
                    "is_current": is_current,
                    "current_version_id": current_version.id,
                    "current_version": current_version.version,
                    "superseded_by": current_version.id if not is_current else None,
                    "effective_date": current_version.effective_date.isoformat() if current_version.effective_date else None
                }

        return {"is_current": True, "superseded_by": None}

    def _calculate_confidence(
        self,
        similarity_score: float,
        match_type: str,
        is_current: bool,
        warning_count: int,
        error_count: int
    ) -> float:
        """Calculate overall confidence score."""
        # Base score from similarity
        confidence = similarity_score

        # Adjust for match type
        if match_type == "exact":
            confidence *= 1.0
        elif match_type == "paraphrase":
            confidence *= 0.9
        elif match_type == "inference":
            confidence *= 0.6
        else:  # not_found
            confidence *= 0.3

        # Penalize for version issues
        if not is_current:
            confidence *= 0.8

        # Penalize for warnings and errors
        confidence *= (1.0 - (warning_count * 0.05))
        confidence *= (1.0 - (error_count * 0.2))

        return max(0.0, min(1.0, confidence))

    def _extract_claims(self, answer: str) -> List[str]:
        """Extract factual claims from LLM answer."""
        # Simple implementation: split by sentences
        # More sophisticated: use NLP to extract claims
        import re
        sentences = re.split(r'[.!?]+', answer)
        return [s.strip() for s in sentences if len(s.strip()) > 20]

    def _find_best_source(self, claim: str, sources: List[dict]) -> dict | None:
        """Find most relevant source for a claim."""
        best_match = None
        best_score = 0.0

        for source in sources:
            excerpt = source.get("excerpt", "")
            if excerpt:
                score = self._calculate_similarity(claim, excerpt)
                if score > best_score:
                    best_score = score
                    best_match = source

        return best_match if best_score > 0.3 else None
```

**1.2 Conflict Detection**

File: `green_gov_rag/verification/conflict_detector.py`

```python
"""Detect conflicts between regulatory documents."""

from dataclasses import dataclass
from typing import List
from sqlmodel import Session, select

from green_gov_rag.models import Document


@dataclass
class RegulatoryConflict:
    """Represents a potential conflict between regulations."""

    document_1: dict
    document_2: dict
    conflict_type: str  # "contradiction", "superseded", "jurisdiction_overlap"
    description: str
    resolution: str  # How to resolve (e.g., "Federal overrides State")
    confidence: float


class ConflictDetector:
    """Detect conflicts and overlaps in regulatory documents."""

    # Regulatory hierarchy
    JURISDICTION_HIERARCHY = {
        "federal": 1,
        "state": 2,
        "local": 3
    }

    def detect_conflicts(
        self,
        primary_doc: dict,
        related_docs: List[dict]
    ) -> List[RegulatoryConflict]:
        """Detect potential conflicts with related documents.

        Args:
            primary_doc: Primary document being cited
            related_docs: Related documents to check against

        Returns:
            List of potential conflicts
        """
        conflicts = []

        for doc in related_docs:
            # Check jurisdiction hierarchy
            if self._check_jurisdiction_conflict(primary_doc, doc):
                conflict = self._create_jurisdiction_conflict(primary_doc, doc)
                conflicts.append(conflict)

            # Check for superseded versions
            if self._check_superseded(primary_doc, doc):
                conflict = self._create_superseded_conflict(primary_doc, doc)
                conflicts.append(conflict)

            # Check topic overlap with different requirements
            if self._check_topic_contradiction(primary_doc, doc):
                conflict = self._create_contradiction_conflict(primary_doc, doc)
                conflicts.append(conflict)

        return conflicts

    def _check_jurisdiction_conflict(self, doc1: dict, doc2: dict) -> bool:
        """Check if documents have overlapping jurisdiction."""
        jurisdiction1 = doc1.get("jurisdiction", "").lower()
        jurisdiction2 = doc2.get("jurisdiction", "").lower()

        # Different jurisdiction levels covering same topic
        if jurisdiction1 != jurisdiction2:
            topic1 = doc1.get("topic", "").lower()
            topic2 = doc2.get("topic", "").lower()
            return topic1 == topic2

        return False

    def _check_superseded(self, doc1: dict, doc2: dict) -> bool:
        """Check if one document supersedes the other."""
        # Would check version history in database
        # For now, simplified check
        return False

    def _check_topic_contradiction(self, doc1: dict, doc2: dict) -> bool:
        """Check if documents contradict on same topic."""
        # Would use NLP to detect contradictions
        # For now, simplified
        return False

    def _create_jurisdiction_conflict(
        self,
        doc1: dict,
        doc2: dict
    ) -> RegulatoryConflict:
        """Create jurisdiction hierarchy conflict."""
        j1 = doc1.get("jurisdiction", "").lower()
        j2 = doc2.get("jurisdiction", "").lower()

        h1 = self.JURISDICTION_HIERARCHY.get(j1, 999)
        h2 = self.JURISDICTION_HIERARCHY.get(j2, 999)

        higher_doc = doc1 if h1 < h2 else doc2
        lower_doc = doc2 if h1 < h2 else doc1

        return RegulatoryConflict(
            document_1=higher_doc,
            document_2=lower_doc,
            conflict_type="jurisdiction_overlap",
            description=f"{higher_doc['jurisdiction'].title()} law may override {lower_doc['jurisdiction']} regulation on this topic",
            resolution=f"Apply {higher_doc['jurisdiction']} requirements; {lower_doc['jurisdiction']} regulations cannot be less stringent",
            confidence=0.8
        )

    # ... implement other conflict creation methods ...
```

**1.3 Enhanced Query Response with Verification**

File: `green_gov_rag/api/services/query_service.py` (additions)

```python
from green_gov_rag.verification.citation_verifier import CitationVerifier
from green_gov_rag.verification.conflict_detector import ConflictDetector

class QueryService:
    def __init__(self):
        # ... existing init ...
        self.citation_verifier = CitationVerifier()
        self.conflict_detector = ConflictDetector()

    def execute_query(self, ...) -> QueryResponse:
        # ... existing query execution ...

        # NEW: Verify citations
        verification_results = self.citation_verifier.verify_response(
            answer=answer,
            sources=source_docs
        )

        # NEW: Check for conflicts
        conflicts = []
        if len(source_docs) > 1:
            conflicts = self.conflict_detector.detect_conflicts(
                primary_doc=source_docs[0],
                related_docs=source_docs[1:]
            )

        # Enrich response with verification metadata
        return QueryResponse(
            query=query,
            answer=answer,
            sources=source_docs,
            filters_applied=metadata_filters,
            response_time_ms=response_time,
            # NEW fields
            citation_verification=verification_results,
            regulatory_conflicts=conflicts,
            overall_confidence=self._calculate_overall_confidence(verification_results)
        )
```

#### Phase 2: Audit Trail & Provenance (Week 2) - 5-7 days

**2.1 Query Provenance Tracking**

File: `green_gov_rag/models/query.py` (additions)

```python
class QueryProvenance(SQLModel, table=True):
    """Track full provenance chain for queries."""

    __tablename__ = "query_provenance"

    id: str = Field(primary_key=True)
    query_id: str = Field(foreign_key="query_history.id")

    # Retrieval provenance
    retrieval_method: str  # "hybrid_search", "semantic", "keyword"
    vector_store_version: str
    embedding_model: str
    top_k: int

    # Retrieved chunks (before reranking)
    retrieved_chunks: list[dict] = Field(sa_column=Column(JSON))
    chunk_scores: list[float] = Field(sa_column=Column(JSON))

    # Reranking
    reranking_method: str | None
    final_chunks: list[dict] = Field(sa_column=Column(JSON))

    # Generation provenance
    llm_model: str
    llm_temperature: float
    system_prompt: str
    user_prompt: str

    # Citation provenance
    citations_verified: bool
    verification_results: dict = Field(sa_column=Column(JSON))

    # Timestamps
    retrieved_at: datetime
    generated_at: datetime
    verified_at: datetime | None

    # Quality metrics
    retrieval_confidence: float
    generation_confidence: float
    overall_confidence: float
```

### Priority Order

**Immediate (MVP - 2 weeks)**:
1. Quote verification base (2 days)
2. Similarity calculation (1 day)
3. Version currency checking (2 days)
4. Confidence scoring (1 day)
5. Basic conflict detection (2 days)
6. Enhanced API response (1 day)
7. Testing (3 days)

**Post-MVP (Month 2)**:
8. Advanced NLP for claim extraction
9. Full provenance tracking
10. Citation audit trail
11. Verification dashboard in admin UI

---

## Implementation Timeline

### Month 1: Core Monitoring Infrastructure
- **Week 1**: Document versioning + base monitor
- **Week 2**: CER monitor + change detection + scheduling
- **Week 3**: Notifications + CLI commands + testing
- **Week 4**: Quote verification + version checking

### Month 2: Advanced Features
- **Week 5**: Additional monitors (NSW EPA, legislation.gov.au)
- **Week 6**: Conflict detection + confidence scoring
- **Week 7**: Admin UI for monitoring
- **Week 8**: Provenance tracking + audit trail

### Month 3: Polish & Launch
- **Week 9**: Integration testing
- **Week 10**: Performance optimization
- **Week 11**: Documentation
- **Week 12**: Production deployment

---

## Success Metrics

### Document Monitoring
- **Coverage**: 95% of configured sources monitored daily
- **Latency**: Updates detected within 24 hours of publication
- **Accuracy**: 99%+ change detection accuracy (no false positives/negatives)
- **Reliability**: 99.9% uptime for monitoring service

### Citation Verification
- **Verification Rate**: 100% of citations automatically verified
- **Confidence**: Average confidence score > 0.85
- **Accuracy**: < 1% false verification failures
- **Conflict Detection**: Identify 90%+ of regulatory conflicts

---

## Dependencies & Configuration

### New Dependencies (add to `pyproject.toml`):

```toml
[tool.poetry.dependencies]
# Monitoring
apscheduler = "^3.10.0"
beautifulsoup4 = "^4.12.0"
aiohttp = "^3.9.0"

# NLP for verification
fuzzywuzzy = "^0.18.0"
python-Levenshtein = "^0.21.0"
spacy = "^3.7.0"  # For advanced claim extraction
```

### Configuration (add to `config.py`):

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Monitoring settings
    monitoring_enabled: bool = True
    monitor_schedule: str = "daily"  # daily/weekly/hourly
    monitor_sources: list[str] = ["cer", "legislation_au", "nsw_epa"]

    # Notification settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    admin_emails: list[str] = []

    # Verification settings
    verification_enabled: bool = True
    citation_similarity_threshold: float = 0.85
    conflict_detection_enabled: bool = True

    # Provenance tracking
    provenance_tracking_enabled: bool = True
```

---

## Competitive Differentiation

With these features, GreenGovRAG becomes:

**vs. Generic RAG (ChatGPT, Claude)**:
- ✅ Automated regulatory tracking (they have none)
- ✅ Citation verification with confidence scores
- ✅ Version-aware responses
- ✅ Regulatory conflict detection

**vs. Legal Tech (LexisNexis, Westlaw)**:
- ✅ Australian government-specific
- ✅ ESG/NGER compliance focus
- ✅ Geospatial LGA filtering
- ✅ Real-time updates (vs. quarterly)

**Market Position**: From "regulatory research assistant" to **"compliance decision support system with guaranteed currency and verifiability"**

---

## Risk Mitigation

**1. Monitoring Reliability**
- Risk: Government websites change structure
- Mitigation: Monitor success/failure rates, alert on degradation
- Fallback: Manual update process still available

**2. False Positives in Change Detection**
- Risk: Minor website changes trigger false updates
- Mitigation: Content hash comparison, not HTML hash
- Fallback: Admin review before processing

**3. Citation Verification Accuracy**
- Risk: LLM paraphrases correctly but fails verification
- Mitigation: Adjustable similarity threshold (0.7-0.95)
- Fallback: Human review for borderline cases

**4. Performance Impact**
- Risk: Verification adds latency to queries
- Mitigation: Async verification, cache results
- Fallback: Make verification optional per query

---

## Testing Strategy

**Unit Tests**:
- Monitor change detection accuracy
- Citation similarity calculations
- Version comparison logic

**Integration Tests**:
- End-to-end monitoring → detection → processing
- Citation verification → conflict detection → response

**Load Tests**:
- 100 concurrent monitoring checks
- 1000 citations verified per minute

**Manual Tests**:
- Test on real government website changes
- Verify citation accuracy on known documents
- Admin UI usability

---

## Documentation Deliverables

1. **API Documentation**: New endpoints for verification
2. **Admin Guide**: How to configure monitoring
3. **Developer Guide**: Adding new monitors
4. **Compliance Guide**: How verification works (for legal review)

---

**Status**: Ready for Implementation
**Estimated Effort**: 3 months (1 developer)
**MVP Timeline**: 4-6 weeks for core monitoring + basic verification

