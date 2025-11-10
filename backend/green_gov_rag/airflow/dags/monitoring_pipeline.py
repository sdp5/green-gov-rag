"""Airflow DAG for automated document monitoring using CLI commands.

This DAG:
- Runs on a configurable schedule (default: daily at 2am)
- Monitors all sources using greengovrag-cli etl monitor
- Detects new and updated documents
- Triggers ETL pipeline for changed documents
- Logs monitoring results

Uses greengovrag-cli commands for consistency with manual operations.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

# --- DAG Default Arguments ---
default_args = {
    "owner": "greengovrag",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


# --- Helper Function ---
def check_for_changes(**context) -> str:
    """Check monitoring output and decide whether to trigger ETL.

    Reads the monitoring command output from XCom and determines
    if any changes were detected.

    Returns:
        'trigger_etl_pipeline' if changes found, 'skip_etl_pipeline' otherwise
    """
    ti = context["task_instance"]

    # Get the bash command output
    output = ti.xcom_pull(task_ids="monitor_sources")

    # Check if output contains change indicators
    # The CLI command will output "Changes detected" if there are updates
    if output and (
        "new documents" in output.lower() or "updated documents" in output.lower()
    ):
        print("Changes detected in monitoring output")
        return "trigger_etl_pipeline"
    else:
        print("No changes detected - skipping ETL")
        return "skip_etl_pipeline"


# --- Main Monitoring DAG ---
with DAG(
    dag_id="greengovrag_monitoring_pipeline",
    default_args=default_args,
    description="Monitor document sources for updates and trigger ETL for changes",
    schedule_interval="0 2 * * *",  # Daily at 2am
    start_date=datetime(2025, 11, 1),
    catchup=False,
    tags=["greengovrag", "monitoring", "etl"],
) as dag:
    # Task 1: Monitor all sources using CLI
    monitor_sources = BashOperator(
        task_id="monitor_sources",
        bash_command="greengovrag-cli etl monitor",
        cwd="/home/sundeep/github/green-gov-rag/backend",
        do_xcom_push=True,  # Push output to XCom for branching decision
    )

    # Task 2: Check if changes were detected
    check_changes = BranchPythonOperator(
        task_id="check_for_changes",
        python_callable=check_for_changes,
        provide_context=True,
    )

    # Task 3a: Trigger ETL pipeline if changes found
    trigger_etl = TriggerDagRunOperator(
        task_id="trigger_etl_pipeline",
        trigger_dag_id="greengovrag_full_pipeline",
        wait_for_completion=False,  # Don't block monitoring DAG
    )

    # Task 3b: Skip ETL if no changes
    skip_etl = BashOperator(
        task_id="skip_etl_pipeline",
        bash_command='echo "No changes detected - ETL pipeline skipped"',
    )

    # Define dependencies
    monitor_sources >> check_changes >> [trigger_etl, skip_etl]


# --- High-Priority Monitoring DAG ---
# This runs more frequently (every 6 hours) for critical regulatory sources
with DAG(
    dag_id="greengovrag_monitoring_high_priority",
    default_args=default_args,
    description="Monitor high-priority sources (regulatory guidelines) more frequently",
    schedule_interval="0 */6 * * *",  # Every 6 hours
    start_date=datetime(2025, 11, 1),
    catchup=False,
    tags=["greengovrag", "monitoring", "high-priority"],
) as high_priority_dag:
    # Monitor high-priority sources
    # NOTE: You can add a --priority flag to the CLI command if needed
    monitor_high_priority = BashOperator(
        task_id="monitor_high_priority_sources",
        bash_command="greengovrag-cli etl monitor",
        cwd="/home/sundeep/github/green-gov-rag/backend",
        do_xcom_push=True,
    )

    # Check for changes
    check_high_priority_changes = BranchPythonOperator(
        task_id="check_high_priority_changes",
        python_callable=check_for_changes,
        provide_context=True,
    )

    # Trigger ETL if needed
    trigger_high_priority_etl = TriggerDagRunOperator(
        task_id="trigger_high_priority_etl",
        trigger_dag_id="greengovrag_full_pipeline",
        wait_for_completion=False,
    )

    # Skip if no changes
    skip_high_priority_etl = BashOperator(
        task_id="skip_high_priority_etl",
        bash_command='echo "No high-priority changes detected - ETL skipped"',
    )

    # Define dependencies
    (
        monitor_high_priority
        >> check_high_priority_changes
        >> [trigger_high_priority_etl, skip_high_priority_etl]
    )
