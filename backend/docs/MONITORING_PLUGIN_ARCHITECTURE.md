# Monitoring Plugin Architecture - Integration Design

## Executive Summary

**Key Insight**: Monitoring capabilities should be **extensions** of existing `DocumentSource` plugins, not separate systems.

**Benefits**:
1. ✅ Single plugin for both ETL **and** monitoring
2. ✅ Community contributors add sources + monitoring together
3. ✅ Leverage existing Airflow infrastructure
4. ✅ Reuse DocumentSourceRegistry pattern
5. ✅ Good first issues for contributors!

---

## Current Architecture Analysis

### Existing: ETL Plugin System

```
DocumentSource (ABC)
├── validate() - Check config
├── get_download_urls() - Static URLs from config
├── get_metadata() - Document metadata
└── [STATIC: Read from documents_config.yml]

Implementations:
├── FederalLegislationSource
├── EmissionsReportingSource
├── StateLegislationSource
└── LocalGovernmentSource

Registry Pattern:
DocumentSourceRegistry → DocumentSourceFactory → Creates sources
```

### Existing: Airflow DAGs

```
green_gov_rag/airflow/dags/
├── etl_pipeline.py - Full ETL workflow
└── etl_pipeline_cloud.py - Cloud storage variant

Current Flow:
1. ingest_docs() - Download from static URLs
2. parse_docs() - Parse PDFs
3. chunk_docs() - Create chunks
4. build_vector_store() - Embed
5. test_rag() - Validate
```

**Gap**: No monitoring, no dynamic discovery, no change detection.

---

## Proposed: Unified Plugin Architecture

### Design Philosophy

> **"A DocumentSource should know how to discover AND download its documents"**

Instead of:
```yaml
# documents_config.yml (static)
- title: CER Guideline
  download_urls:
    - https://cer.gov.au/doc.pdf  # Hardcoded!
```

We extend to:
```python
# Plugin knows HOW to find documents
class CERSource(DocumentSource, MonitorableSource):
    def discover_documents(self) -> list[DiscoveredDocument]:
        """Scrape CER website for current guidelines."""

    def check_for_updates(self, known_doc: dict) -> ChangeDetectionResult:
        """Check if document has changed."""
```

---

## Implementation Plan

### Phase 1: Extend DocumentSource Base (2-3 days)

**File**: `green_gov_rag/etl/sources/base.py`

```python
"""Enhanced base interface with monitoring capabilities."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class DiscoveredDocument:
    """Represents a document discovered by monitoring."""

    title: str
    url: str
    discovered_at: datetime
    last_modified: datetime | None = None
    content_hash: str | None = None
    file_size: int | None = None
    version: str | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ChangeDetectionResult:
    """Result of checking if a document has changed."""

    has_changed: bool
    change_type: str | None = None  # "new", "updated", "metadata_only"
    current_hash: str | None = None
    previous_hash: str | None = None
    current_size: int | None = None
    previous_size: int | None = None
    last_modified: datetime | None = None
    details: dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class MonitorableSource(ABC):
    """Mixin for document sources that support automated monitoring.

    This is an OPTIONAL interface. Sources that don't support monitoring
    can still inherit from DocumentSource without implementing this.

    Community contributors can implement this for "good first issues"!

    Example:
        >>> class CERSource(DocumentSource, MonitorableSource):
        ...     def discover_documents(self):
        ...         # Scrape CER website
        ...         return [DiscoveredDocument(...)]
        ...
        ...     def check_for_updates(self, known_doc):
        ...         # Compare hashes
        ...         return ChangeDetectionResult(has_changed=True)
    """

    @abstractmethod
    def discover_documents(self) -> list[DiscoveredDocument]:
        """Discover documents from this source dynamically.

        This method should scrape/query the source website/API to find
        all currently available documents.

        Returns:
            List of discovered documents with metadata

        Example Implementation:
            >>> def discover_documents(self):
            ...     # Scrape CER website
            ...     response = requests.get(self.GUIDELINES_URL)
            ...     soup = BeautifulSoup(response.text)
            ...     pdf_links = soup.find_all('a', href=lambda x: x.endswith('.pdf'))
            ...
            ...     return [
            ...         DiscoveredDocument(
            ...             title=link.text,
            ...             url=link['href'],
            ...             discovered_at=datetime.utcnow()
            ...         ) for link in pdf_links
            ...     ]
        """
        pass

    @abstractmethod
    def check_for_updates(
        self,
        known_document: dict[str, Any]
    ) -> ChangeDetectionResult:
        """Check if a known document has been updated at the source.

        Args:
            known_document: Dictionary with document metadata including:
                - url: Document URL
                - content_hash: Previous content hash
                - last_checked: Last check timestamp

        Returns:
            ChangeDetectionResult indicating if document changed

        Example Implementation:
            >>> def check_for_updates(self, known_document):
            ...     # Download current version
            ...     response = requests.get(known_document['url'])
            ...     current_hash = hashlib.sha256(response.content).hexdigest()
            ...
            ...     has_changed = current_hash != known_document.get('content_hash')
            ...
            ...     return ChangeDetectionResult(
            ...         has_changed=has_changed,
            ...         change_type="updated" if has_changed else None,
            ...         current_hash=current_hash,
            ...         previous_hash=known_document.get('content_hash')
            ...     )
        """
        pass

    def supports_monitoring(self) -> bool:
        """Check if this source supports automated monitoring.

        Returns:
            True if discover_documents and check_for_updates are implemented
        """
        # Check if methods are implemented (not abstract)
        try:
            # Call with dummy args to see if implemented
            return True
        except NotImplementedError:
            return False

    def get_monitoring_schedule(self) -> str:
        """Get recommended monitoring schedule for this source.

        Returns:
            Cron expression (default: daily at 2 AM)

        Override this for sources that need more frequent monitoring:
            >>> def get_monitoring_schedule(self):
            ...     return "0 */6 * * *"  # Every 6 hours
        """
        return "0 2 * * *"  # Daily at 2 AM

    def get_monitoring_priority(self) -> str:
        """Get monitoring priority level.

        Returns:
            "high", "medium", or "low"

        High priority sources are monitored more frequently.
        """
        return "medium"


class DocumentSource(ABC):
    """Base interface for document sources.

    UNCHANGED: All existing functionality preserved.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def validate(self) -> ValidationResult:
        pass

    @abstractmethod
    def get_download_urls(self) -> list[str]:
        pass

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        pass

    def get_source_type(self) -> str:
        return self.__class__.__name__.replace("Source", "").lower()

    # ... existing methods unchanged ...

    # NEW: Optional monitoring check
    def is_monitorable(self) -> bool:
        """Check if this source supports automated monitoring.

        Returns:
            True if source implements MonitorableSource interface
        """
        return isinstance(self, MonitorableSource)
```

### Phase 2: Implement Monitorable Sources (Good First Issues!)

#### Example 1: CER Source (3-4 days)

**File**: `green_gov_rag/etl/sources/emissions.py`

```python
"""Enhanced emissions sources with monitoring."""

import hashlib
import logging
from datetime import datetime
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from green_gov_rag.etl.sources.base import (
    DocumentSource,
    MonitorableSource,
    DiscoveredDocument,
    ChangeDetectionResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class CEREmissionsSource(DocumentSource, MonitorableSource):
    """Clean Energy Regulator emissions reporting guidelines.

    Monitors: https://www.cleanenergyregulator.gov.au/NGER/

    This source demonstrates the monitoring pattern for community contributors.
    """

    # Class constants for monitoring
    BASE_URL = "https://www.cleanenergyregulator.gov.au"
    GUIDELINES_URL = (
        f"{BASE_URL}/NGER/About-the-National-Greenhouse-and-Energy-Reporting-scheme/"
        "Measurement-guidelines"
    )

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self._cache: dict[str, Any] = {}

    # === DocumentSource interface (required) ===

    def validate(self) -> ValidationResult:
        """Validate CER source configuration."""
        errors = []
        warnings = []

        # Check required fields
        errors.extend(self._validate_required_fields())

        # Check esg_metadata presence
        esg_metadata = self.config.get("esg_metadata", {})
        if not esg_metadata:
            warnings.append("Missing esg_metadata for CER document")

        # Check regulator field
        if esg_metadata.get("regulator") != "Clean Energy Regulator":
            warnings.append("Expected regulator: 'Clean Energy Regulator'")

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult(is_valid=True, errors=[], warnings=warnings)

    def get_download_urls(self) -> list[str]:
        """Get configured download URLs (static fallback)."""
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict[str, Any]:
        """Get document metadata."""
        return {
            "title": self.config.get("title", ""),
            "jurisdiction": self.config.get("jurisdiction", "federal"),
            "category": self.config.get("category", "environment"),
            "topic": self.config.get("topic", "emissions_reporting"),
            "esg_metadata": self.config.get("esg_metadata", {}),
            "source_url": self.config.get("source_url", self.GUIDELINES_URL),
        }

    # === MonitorableSource interface (monitoring capabilities) ===

    async def discover_documents(self) -> list[DiscoveredDocument]:
        """Discover CER guidelines by scraping the website.

        This is a GOOD FIRST ISSUE template for contributors!

        Returns:
            List of discovered PDF guidelines
        """
        discovered = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.GUIDELINES_URL) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch CER guidelines: HTTP {response.status}")
                        return discovered

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Find all PDF links in the guidelines section
                    # Look for links containing keywords: "guideline", "measurement", "scope"
                    pdf_links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf'))

                    for link in pdf_links:
                        href = link.get('href', '')
                        title = link.get_text(strip=True)

                        # Make absolute URL
                        if not href.startswith('http'):
                            href = self.BASE_URL + href

                        # Filter for relevant documents
                        if any(keyword in title.lower() for keyword in
                               ['scope', 'emission', 'nger', 'measurement', 'guideline']):

                            discovered.append(DiscoveredDocument(
                                title=title,
                                url=href,
                                discovered_at=datetime.utcnow(),
                                metadata={
                                    "source": "CER",
                                    "scrape_url": self.GUIDELINES_URL,
                                    "link_text": title,
                                }
                            ))

            logger.info(f"Discovered {len(discovered)} CER guidelines")

        except Exception as e:
            logger.error(f"Error discovering CER documents: {e}", exc_info=True)

        return discovered

    async def check_for_updates(
        self,
        known_document: dict[str, Any]
    ) -> ChangeDetectionResult:
        """Check if a CER guideline has been updated.

        Args:
            known_document: Dict with 'url', 'content_hash', 'last_checked'

        Returns:
            ChangeDetectionResult with update status
        """
        url = known_document.get('url')
        previous_hash = known_document.get('content_hash')

        if not url:
            return ChangeDetectionResult(
                has_changed=False,
                details={"error": "No URL provided"}
            )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return ChangeDetectionResult(
                            has_changed=False,
                            details={"error": f"HTTP {response.status}"}
                        )

                    content = await response.read()
                    current_hash = hashlib.sha256(content).hexdigest()
                    current_size = len(content)

                    has_changed = previous_hash is None or current_hash != previous_hash

                    change_type = None
                    if previous_hash is None:
                        change_type = "new"
                    elif has_changed:
                        change_type = "updated"

                    return ChangeDetectionResult(
                        has_changed=has_changed,
                        change_type=change_type,
                        current_hash=current_hash,
                        previous_hash=previous_hash,
                        current_size=current_size,
                        previous_size=known_document.get('file_size'),
                        last_modified=datetime.utcnow(),
                        details={
                            "url": url,
                            "method": "content_hash"
                        }
                    )

        except Exception as e:
            logger.error(f"Error checking CER document updates: {e}", exc_info=True)
            return ChangeDetectionResult(
                has_changed=False,
                details={"error": str(e)}
            )

    def get_monitoring_schedule(self) -> str:
        """CER guidelines are high priority - check every 6 hours."""
        return "0 */6 * * *"

    def get_monitoring_priority(self) -> str:
        """CER is high priority for emissions compliance."""
        return "high"


# GOOD FIRST ISSUE: NSW EPA Source
class NSWEPAEmissionsSource(DocumentSource, MonitorableSource):
    """NSW EPA emissions guidelines.

    TODO: Implement monitoring for NSW EPA website.

    Good First Issue for contributors!

    Reference URL: https://www.epa.nsw.gov.au/your-environment/climate-change

    Implementation Guide:
    1. Set BASE_URL and GUIDELINES_URL
    2. Implement discover_documents():
       - Scrape EPA website for PDFs
       - Filter for climate/emissions related
       - Return DiscoveredDocument list
    3. Implement check_for_updates():
       - Download current version
       - Compare SHA256 hash
       - Return ChangeDetectionResult
    4. Test with: pytest tests/etl/sources/test_nsw_epa_monitor.py
    """

    BASE_URL = "https://www.epa.nsw.gov.au"
    GUIDELINES_URL = f"{BASE_URL}/your-environment/climate-change"

    def validate(self) -> ValidationResult:
        # TODO: Implement validation
        return ValidationResult.success()

    def get_download_urls(self) -> list[str]:
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict[str, Any]:
        return {
            "title": self.config.get("title", ""),
            "jurisdiction": "state",
            "region": "New South Wales",
        }

    async def discover_documents(self) -> list[DiscoveredDocument]:
        # TODO: Implement NSW EPA scraping
        # HINT: Look for PDFs in the climate change section
        # HINT: Use aiohttp + BeautifulSoup like CEREmissionsSource
        raise NotImplementedError("TODO: Implement NSW EPA monitoring")

    async def check_for_updates(self, known_document: dict[str, Any]) -> ChangeDetectionResult:
        # TODO: Implement change detection
        raise NotImplementedError("TODO: Implement NSW EPA change detection")


# Backward compatibility - keep existing class
class EmissionsReportingSource(DocumentSource):
    """Generic emissions source (no monitoring).

    This is the original class - preserved for backward compatibility.
    Use CEREmissionsSource for monitoring-capable version.
    """

    def validate(self) -> ValidationResult:
        errors = []
        warnings = []
        errors.extend(self._validate_required_fields())
        errors.extend(self._validate_urls())

        esg_metadata = self.config.get("esg_metadata", {})
        if not esg_metadata:
            warnings.append("Missing 'esg_metadata' for emissions document")

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult(is_valid=True, errors=[], warnings=warnings)

    def get_download_urls(self) -> list[str]:
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict[str, Any]:
        return {
            "title": self.config.get("title", ""),
            "source_url": self.config.get("source_url", ""),
            "jurisdiction": self.config.get("jurisdiction", ""),
            "category": self.config.get("category", ""),
            "topic": self.config.get("topic", ""),
            "esg_metadata": self.config.get("esg_metadata", {}),
        }
```

#### Example 2: Legislation.gov.au Source (Good First Issue!)

**File**: `green_gov_rag/etl/sources/federal.py`

```python
"""Federal legislation sources with monitoring."""

from green_gov_rag.etl.sources.base import (
    DocumentSource,
    MonitorableSource,
    DiscoveredDocument,
    ChangeDetectionResult,
)


class LegislationAUSource(DocumentSource, MonitorableSource):
    """Federal legislation from legislation.gov.au with RSS monitoring.

    GOOD FIRST ISSUE: Implement RSS feed monitoring for federal acts.

    Reference: https://www.legislation.gov.au/rss/latest-updates

    Implementation Guide:
    1. Parse RSS feed XML
    2. Filter for environmental/climate acts
    3. Extract title, link, pubDate
    4. Return DiscoveredDocument list
    """

    BASE_URL = "https://www.legislation.gov.au"
    RSS_FEED = f"{BASE_URL}/rss/latest-updates"

    async def discover_documents(self) -> list[DiscoveredDocument]:
        """Discover new legislation from RSS feed.

        TODO: Implement RSS parsing
        HINT: Use aiohttp + xml.etree.ElementTree
        HINT: Filter for keywords: environment, climate, emissions
        """
        raise NotImplementedError("TODO: Implement legislation.gov.au RSS monitoring")

    async def check_for_updates(self, known_document: dict) -> ChangeDetectionResult:
        """Check if legislation has been amended."""
        # TODO: Check for amendment history
        raise NotImplementedError("TODO: Implement amendment detection")

    # ... other methods ...
```

### Phase 3: Airflow Integration (3-4 days)

**File**: `green_gov_rag/airflow/dags/document_monitoring.py`

```python
"""Airflow DAG for automated document monitoring.

This DAG uses the MonitorableSource interface to check for updates
across all registered document sources.
"""

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlmodel import Session, select

from green_gov_rag.etl.sources.factory import DocumentSourceFactory
from green_gov_rag.etl.sources.loader import load_document_sources
from green_gov_rag.models import Document
from green_gov_rag.models.base import engine

logger = logging.getLogger(__name__)


default_args = {
    "owner": "greengovrag",
    "depends_on_past": False,
    "email_on_failure": True,
    "email": ["admin@greengovrag.com"],  # Configure in Airflow
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# Main monitoring DAG - runs daily
monitoring_dag = DAG(
    "document_monitoring_daily",
    default_args=default_args,
    description="Check all monitorable sources for document updates",
    schedule_interval="0 2 * * *",  # Daily at 2 AM
    start_date=datetime(2025, 10, 15),
    catchup=False,
    tags=["monitoring", "documents"],
)


def task_discover_new_documents(**context):
    """Discover new documents from all monitorable sources.

    This task calls discover_documents() on each MonitorableSource
    and saves any newly discovered documents to the database.
    """
    factory = DocumentSourceFactory()
    sources = load_document_sources()

    discovered_total = 0
    new_documents = []

    for source in sources:
        if not source.is_monitorable():
            logger.info(f"Skipping non-monitorable source: {source.get_source_type()}")
            continue

        try:
            logger.info(f"Discovering documents from: {source.get_source_type()}")
            discovered = await source.discover_documents()

            # Check if documents are already known
            with Session(engine) as session:
                for doc in discovered:
                    # Query database for existing document
                    stmt = select(Document).where(Document.source_url == doc.url)
                    existing = session.exec(stmt).first()

                    if not existing:
                        # New document found!
                        logger.info(f"NEW DOCUMENT: {doc.title}")

                        # Create database record
                        new_doc = Document(
                            id=f"doc_{datetime.utcnow().timestamp()}",
                            title=doc.title,
                            source_url=doc.url,
                            status="pending",
                            monitor_enabled=True,
                            content_hash=doc.content_hash,
                            **source.get_metadata()
                        )
                        session.add(new_doc)
                        new_documents.append(doc.title)

                session.commit()

            discovered_total += len(discovered)

        except Exception as e:
            logger.error(f"Error discovering from {source.get_source_type()}: {e}")

    # Push to XCom for downstream tasks
    context['task_instance'].xcom_push(
        key='discovered_count',
        value=discovered_total
    )
    context['task_instance'].xcom_push(
        key='new_documents',
        value=new_documents
    )

    logger.info(f"Discovery complete: {discovered_total} total, {len(new_documents)} new")


def task_check_for_updates(**context):
    """Check existing documents for updates.

    This task calls check_for_updates() on each monitored document
    and detects content changes.
    """
    factory = DocumentSourceFactory()

    updated_count = 0
    updated_documents = []

    with Session(engine) as session:
        # Get all monitored documents
        stmt = select(Document).where(
            Document.monitor_enabled == True,
            Document.status != "failed"
        )
        documents = session.exec(stmt).all()

        logger.info(f"Checking {len(documents)} documents for updates")

        for doc in documents:
            try:
                # Get appropriate source
                source = factory.create_source({
                    "title": doc.title,
                    "source_url": doc.source_url,
                    "jurisdiction": doc.jurisdiction,
                    "category": doc.category,
                    "topic": doc.topic,
                })

                if not source.is_monitorable():
                    continue

                # Check for updates
                result = await source.check_for_updates({
                    "url": doc.source_url,
                    "content_hash": doc.content_hash,
                    "last_checked": doc.last_checked,
                })

                # Update last_checked timestamp
                doc.last_checked = datetime.utcnow()

                if result.has_changed:
                    logger.info(f"UPDATE DETECTED: {doc.title}")
                    updated_count += 1
                    updated_documents.append(doc.title)

                    # Update document metadata
                    doc.content_hash = result.current_hash
                    doc.status = "pending"  # Queue for reprocessing

                session.add(doc)

            except Exception as e:
                logger.error(f"Error checking {doc.title}: {e}")

        session.commit()

    # Push to XCom
    context['task_instance'].xcom_push(key='updated_count', value=updated_count)
    context['task_instance'].xcom_push(key='updated_documents', value=updated_documents)

    logger.info(f"Update check complete: {updated_count} updates found")


def task_send_notification(**context):
    """Send notification email to admins about monitoring results."""
    ti = context['task_instance']

    discovered_count = ti.xcom_pull(task_ids='discover_new_documents', key='discovered_count')
    new_documents = ti.xcom_pull(task_ids='discover_new_documents', key='new_documents')
    updated_count = ti.xcom_pull(task_ids='check_for_updates', key='updated_count')
    updated_documents = ti.xcom_pull(task_ids='check_for_updates', key='updated_documents')

    if discovered_count == 0 and updated_count == 0:
        logger.info("No updates found, skipping notification")
        return

    # Build notification message
    message = f"""
Document Monitoring Summary - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

New Documents Discovered: {len(new_documents) if new_documents else 0}
{chr(10).join([f"  - {doc}" for doc in (new_documents or [])[:10]])}

Documents Updated: {updated_count}
{chr(10).join([f"  - {doc}" for doc in (updated_documents or [])[:10]])}

Next Steps:
- New/updated documents are queued for processing
- Run the ETL pipeline to process pending documents
- Check the admin dashboard for details

View pending documents: http://localhost:8000/admin/documents?status=pending
"""

    # TODO: Integrate with notification service (email, Slack, etc.)
    logger.info(f"Notification message:\\n{message}")

    # For now, just print (would send email in production)
    print(message)


def task_trigger_etl_for_updates(**context):
    """Trigger ETL pipeline for updated documents.

    This creates a new DAG run for the ETL pipeline to process
    any documents marked as 'pending'.
    """
    from airflow.api.common.trigger_dag import trigger_dag

    ti = context['task_instance']
    updated_count = ti.xcom_pull(task_ids='check_for_updates', key='updated_count')

    if updated_count > 0:
        # Trigger ETL DAG
        trigger_dag(
            dag_id="greengovrag_full_pipeline",
            run_id=f"monitoring_triggered_{datetime.utcnow().timestamp()}",
            conf={"triggered_by": "monitoring", "process_pending_only": True}
        )
        logger.info(f"Triggered ETL pipeline for {updated_count} updated documents")


# Define tasks
discover_task = PythonOperator(
    task_id="discover_new_documents",
    python_callable=task_discover_new_documents,
    dag=monitoring_dag,
)

check_updates_task = PythonOperator(
    task_id="check_for_updates",
    python_callable=task_check_for_updates,
    dag=monitoring_dag,
)

notify_task = PythonOperator(
    task_id="send_notification",
    python_callable=task_send_notification,
    dag=monitoring_dag,
)

trigger_etl_task = PythonOperator(
    task_id="trigger_etl_for_updates",
    python_callable=task_trigger_etl_for_updates,
    dag=monitoring_dag,
)

# Define dependencies
[discover_task, check_updates_task] >> notify_task >> trigger_etl_task


# High-priority sources DAG - runs every 6 hours
high_priority_dag = DAG(
    "document_monitoring_high_priority",
    default_args=default_args,
    description="Monitor high-priority sources (CER, federal legislation)",
    schedule_interval="0 */6 * * *",  # Every 6 hours
    start_date=datetime(2025, 10, 15),
    catchup=False,
    tags=["monitoring", "high-priority"],
)


def task_monitor_high_priority(**context):
    """Monitor only high-priority sources."""
    factory = DocumentSourceFactory()
    sources = load_document_sources()

    high_priority_sources = [
        s for s in sources
        if s.is_monitorable() and s.get_monitoring_priority() == "high"
    ]

    logger.info(f"Monitoring {len(high_priority_sources)} high-priority sources")

    # Run same check_for_updates logic but only for high-priority
    # ... (similar to task_check_for_updates but filtered)


high_priority_task = PythonOperator(
    task_id="monitor_high_priority",
    python_callable=task_monitor_high_priority,
    dag=high_priority_dag,
)
```

### Phase 4: Enhanced ETL Pipeline (2 days)

**File**: `green_gov_rag/airflow/dags/etl_pipeline.py` (enhanced)

```python
"""Enhanced ETL pipeline with monitoring integration."""

# ... existing imports ...
from green_gov_rag.etl.sources.loader import load_document_sources
from sqlmodel import Session, select
from green_gov_rag.models import Document

def task_ingest_docs(**context) -> None:
    """Enhanced: Download ONLY pending documents."""

    # Check if triggered by monitoring
    conf = context.get('dag_run').conf or {}
    process_pending_only = conf.get('process_pending_only', False)

    if process_pending_only:
        # Only process documents marked as pending
        with Session(engine) as session:
            stmt = select(Document).where(Document.status == "pending")
            pending_docs = session.exec(stmt).all()

            logger.info(f"Processing {len(pending_docs)} pending documents")

            RAW_DIR.mkdir(parents=True, exist_ok=True)

            for doc in pending_docs:
                try:
                    # Download document
                    ingest.download_document(doc.source_url, str(RAW_DIR))

                    # Mark as processing
                    doc.status = "processing"
                    session.add(doc)

                except Exception as e:
                    logger.error(f"Failed to download {doc.title}: {e}")
                    doc.status = "failed"
                    doc.error_message = str(e)
                    session.add(doc)

            session.commit()
    else:
        # Original behavior: download all from config
        docs = loader.load_documents_config(CONFIG_PATH)
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        ingest.download_documents(docs, str(RAW_DIR))

# ... rest of pipeline unchanged ...
```

---

## Community Contribution Guide

### Good First Issues Template

**Issue #1: Implement NSW EPA Monitoring**

```markdown
## Description
Add monitoring support for NSW EPA emissions guidelines.

## Background
We have a plugin architecture for document sources. Sources that implement
`MonitorableSource` can be automatically monitored for updates.

## Task
Implement monitoring for NSW EPA website:
- URL: https://www.epa.nsw.gov.au/your-environment/climate-change
- Source file: `green_gov_rag/etl/sources/emissions.py`
- Class: `NSWEPAEmissionsSource`

## What to Implement
1. `discover_documents()` - Scrape EPA website for PDF guidelines
2. `check_for_updates()` - Compare content hashes to detect changes

## Reference Implementation
See `CEREmissionsSource` in the same file for a complete example.

## Testing
```bash
pytest tests/etl/sources/test_nsw_epa_monitor.py
```

## Acceptance Criteria
- [ ] `discover_documents()` finds all climate-related PDFs
- [ ] `check_for_updates()` correctly detects content changes
- [ ] Unit tests pass
- [ ] Integration test with Airflow succeeds

## Resources
- [MonitorableSource Interface](docs/MONITORING_PLUGIN_ARCHITECTURE.md#monitorablesource)
- [CER Source Example](green_gov_rag/etl/sources/emissions.py#L50)
- [Testing Guide](tests/etl/sources/README.md)

## Estimated Effort
4-6 hours

## Labels
`good first issue`, `monitoring`, `help wanted`, `hacktoberfest`
```

---

## Benefits of This Architecture

### 1. Unified Codebase
- ✅ One plugin does ETL **and** monitoring
- ✅ No duplicate code for URL discovery
- ✅ Community contributors add both at once

### 2. Leverage Existing Infrastructure
- ✅ Airflow already set up
- ✅ DocumentSourceRegistry pattern reused
- ✅ Factory pattern handles both modes

### 3. Gradual Adoption
- ✅ Existing `DocumentSource` plugins work as-is
- ✅ `MonitorableSource` is optional mixin
- ✅ Sources added incrementally

### 4. Community-Friendly
- ✅ Clear plugin template (CEREmissionsSource)
- ✅ Good first issues with examples
- ✅ Well-defined interface
- ✅ Testing infrastructure provided

### 5. Scalable
- ✅ Each source defines its own schedule
- ✅ Priority levels for high-value sources
- ✅ Airflow handles orchestration
- ✅ Parallel execution out of the box

---

## Migration Path

### Week 1: Add MonitorableSource Interface
- Update `etl/sources/base.py`
- Add `DiscoveredDocument` and `ChangeDetectionResult` dataclasses
- No breaking changes to existing sources

### Week 2: Implement CER Monitoring (Template)
- Create `CEREmissionsSource` as reference implementation
- Add unit tests
- Document contribution process

### Week 3: Airflow DAGs
- Create `document_monitoring.py` DAG
- Integrate with existing ETL pipeline
- Test end-to-end flow

### Week 4: Community Rollout
- Create "good first issues" for NSW EPA, VIC EPA, legislation.gov.au
- Write contributor guide
- Add templates to GitHub

---

## Testing Strategy

### Unit Tests

```python
# tests/etl/sources/test_cer_monitor.py

import pytest
from green_gov_rag.etl.sources.emissions import CEREmissionsSource

@pytest.mark.asyncio
async def test_cer_discover_documents():
    """Test CER document discovery."""
    source = CEREmissionsSource({
        "title": "Test CER Source",
        "jurisdiction": "federal",
    })

    documents = await source.discover_documents()

    assert len(documents) > 0
    assert all(doc.url.endswith('.pdf') for doc in documents)
    assert all('scope' in doc.title.lower() or 'nger' in doc.title.lower()
               for doc in documents)

@pytest.mark.asyncio
async def test_cer_check_for_updates_no_change():
    """Test change detection when document unchanged."""
    source = CEREmissionsSource({})

    known_doc = {
        "url": "https://cer.gov.au/test.pdf",
        "content_hash": "abc123",
    }

    result = await source.check_for_updates(known_doc)

    # Mock would return same hash
    assert result.has_changed == False
```

### Integration Tests

```python
# tests/airflow/test_monitoring_dag.py

def test_monitoring_dag_loads():
    """Test that monitoring DAG can be loaded."""
    from airflow.models import DagBag

    dagbag = DagBag(dag_folder='green_gov_rag/airflow/dags/')

    assert 'document_monitoring_daily' in dagbag.dags
    assert dagbag.import_errors == {}

def test_monitoring_dag_structure():
    """Test DAG has correct task structure."""
    from green_gov_rag.airflow.dags.document_monitoring import monitoring_dag

    tasks = [task.task_id for task in monitoring_dag.tasks]

    assert 'discover_new_documents' in tasks
    assert 'check_for_updates' in tasks
    assert 'send_notification' in tasks
```

---

## Summary

**Q1**: Is integrating monitoring with plugin architecture a good idea?
**A**: **YES!** It's better than a separate monitoring system because:
- Single source of truth per government website
- Contributors add source + monitoring together
- Leverages existing registry pattern
- Reuses Airflow infrastructure

**Q2**: How does integration look?
**A**:
1. **Interface**: Add `MonitorableSource` mixin to `DocumentSource`
2. **Plugins**: Sources like `CEREmissionsSource` implement both ETL and monitoring
3. **Airflow**: New DAG calls `discover_documents()` and `check_for_updates()`
4. **Community**: "Good first issues" follow CER template
5. **Gradual**: Existing sources work without changes, add monitoring incrementally

**Key Files**:
- `etl/sources/base.py` - Add `MonitorableSource` interface
- `etl/sources/emissions.py` - Implement `CEREmissionsSource` as template
- `airflow/dags/document_monitoring.py` - New monitoring DAG
- `docs/MONITORING_PLUGIN_ARCHITECTURE.md` - This document!

**Timeline**: 3-4 weeks for core + template, then community adds sources over time.

