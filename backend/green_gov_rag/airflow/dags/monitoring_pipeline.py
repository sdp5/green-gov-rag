"""Airflow DAG for automated document monitoring.

This DAG:
- Runs on a configurable schedule (default: daily at 2am)
- Monitors all sources that implement MonitorableSource
- Detects new and updated documents
- Triggers ETL pipeline for changed documents
- Logs monitoring results
"""

import asyncio
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from green_gov_rag.api.services.monitoring_service import MonitoringService

# --- DAG Default Arguments ---
default_args = {
    "owner": "sundeep",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# --- DAG Definition ---
dag = DAG(
    "greengovrag_monitoring_pipeline",
    description="Monitor document sources for updates and trigger ETL for changes",
    start_date=datetime(2025, 10, 15),
    schedule_interval="0 2 * * *",  # Daily at 2am
    default_args=default_args,
    catchup=False,
    tags=["monitoring", "etl", "documents"],
)


# --- Helper Functions ---
def run_async(coro):
    """Helper to run async coroutines in Airflow tasks."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


# --- Task Functions ---
def task_monitor_all_sources(**context) -> dict:
    """Monitor all registered document sources.

    Returns:
        Dictionary with monitoring results
    """
    service = MonitoringService()
    results = run_async(service.monitor_all_sources())

    # Push results to XCom for downstream tasks
    context["task_instance"].xcom_push(key="monitoring_results", value=results)

    return results


def task_check_for_changes(**context) -> str:
    """Check if any documents were discovered or updated.

    Returns:
        'trigger_etl' if changes found, 'skip_etl' otherwise
    """
    ti = context["task_instance"]
    results = ti.xcom_pull(key="monitoring_results", task_ids="monitor_sources")

    total_discovered = results.get("total_discovered", 0)
    total_updated = results.get("total_updated", 0)

    if total_discovered > 0 or total_updated > 0:
        print(
            f"Changes detected: {total_discovered} new, {total_updated} updated documents"
        )
        return "trigger_etl_pipeline"
    else:
        print("No changes detected - skipping ETL")
        return "skip_etl_pipeline"


def task_monitor_high_priority(**context) -> dict:
    """Monitor high-priority sources (regulatory guidelines).

    High-priority sources are checked more frequently and processed first.
    """
    service = MonitoringService()

    # Get all sources and filter for high priority
    # For now, this would need to be configured per source
    # In a real implementation, you'd query sources and filter by priority
    results = run_async(service.monitor_all_sources())

    # Filter for high-priority results
    high_priority_results = {
        "source_results": [
            r for r in results.get("source_results", []) if r.get("priority") == "high"
        ]
    }

    context["task_instance"].xcom_push(
        key="high_priority_results", value=high_priority_results
    )

    return high_priority_results


def task_log_monitoring_summary(**context) -> None:
    """Log summary of monitoring results."""
    ti = context["task_instance"]
    results = ti.xcom_pull(key="monitoring_results", task_ids="monitor_sources")

    print("=" * 70)
    print("MONITORING SUMMARY")
    print("=" * 70)
    print(f"Total sources checked: {results.get('sources_checked', 0)}")
    print(f"Sources failed: {results.get('sources_failed', 0)}")
    print(f"Documents discovered: {results.get('total_discovered', 0)}")
    print(f"Documents updated: {results.get('total_updated', 0)}")
    print(f"Documents unchanged: {results.get('total_unchanged', 0)}")
    print("=" * 70)

    # Log per-source details
    for source_result in results.get("source_results", []):
        print(f"\n{source_result['source_type']}:")
        print(f"  Status: {source_result['status']}")
        print(f"  Discovered: {source_result.get('documents_discovered', 0)}")
        print(f"  Updated: {source_result.get('documents_updated', 0)}")
        print(f"  Duration: {source_result.get('duration_seconds', 0):.2f}s")


def task_skip_etl(**context) -> None:
    """Log that ETL was skipped."""
    print("No changes detected - ETL pipeline skipped")


# --- Operators ---

# 1. Monitor all sources
monitor_sources = PythonOperator(
    task_id="monitor_sources",
    python_callable=task_monitor_all_sources,
    dag=dag,
    provide_context=True,
)

# 2. Check if changes were found
check_changes = BranchPythonOperator(
    task_id="check_for_changes",
    python_callable=task_check_for_changes,
    dag=dag,
    provide_context=True,
)

# 3a. Trigger ETL pipeline if changes found
trigger_etl = TriggerDagRunOperator(
    task_id="trigger_etl_pipeline",
    trigger_dag_id="greengovrag_full_pipeline",  # Reference to existing ETL DAG
    wait_for_completion=False,  # Don't block monitoring DAG
    dag=dag,
)

# 3b. Skip ETL if no changes
skip_etl = PythonOperator(
    task_id="skip_etl_pipeline",
    python_callable=task_skip_etl,
    dag=dag,
    provide_context=True,
)

# 4. Log summary (runs regardless of branch)
log_summary = PythonOperator(
    task_id="log_monitoring_summary",
    python_callable=task_log_monitoring_summary,
    dag=dag,
    provide_context=True,
    trigger_rule="none_failed",  # Run even if ETL was skipped
)

# --- Dependencies ---
monitor_sources >> check_changes
check_changes >> [trigger_etl, skip_etl]
[trigger_etl, skip_etl] >> log_summary


# --- Optional: Separate DAG for High-Priority Monitoring ---
# This runs more frequently (every 6 hours) for critical regulatory sources

high_priority_dag = DAG(
    "greengovrag_monitoring_high_priority",
    description="Monitor high-priority sources (regulatory guidelines) more frequently",
    start_date=datetime(2025, 10, 15),
    schedule_interval="0 */6 * * *",  # Every 6 hours
    default_args=default_args,
    catchup=False,
    tags=["monitoring", "high-priority", "regulatory"],
)

monitor_high_priority = PythonOperator(
    task_id="monitor_high_priority_sources",
    python_callable=task_monitor_high_priority,
    dag=high_priority_dag,
    provide_context=True,
)

check_high_priority_changes = BranchPythonOperator(
    task_id="check_high_priority_changes",
    python_callable=task_check_for_changes,
    dag=high_priority_dag,
    provide_context=True,
)

trigger_high_priority_etl = TriggerDagRunOperator(
    task_id="trigger_high_priority_etl",
    trigger_dag_id="greengovrag_full_pipeline",
    wait_for_completion=False,
    dag=high_priority_dag,
)

skip_high_priority_etl = PythonOperator(
    task_id="skip_high_priority_etl",
    python_callable=task_skip_etl,
    dag=high_priority_dag,
    provide_context=True,
)

log_high_priority_summary = PythonOperator(
    task_id="log_high_priority_summary",
    python_callable=task_log_monitoring_summary,
    dag=high_priority_dag,
    provide_context=True,
    trigger_rule="none_failed",
)

# High-priority DAG dependencies
monitor_high_priority >> check_high_priority_changes
check_high_priority_changes >> [trigger_high_priority_etl, skip_high_priority_etl]
[trigger_high_priority_etl, skip_high_priority_etl] >> log_high_priority_summary
