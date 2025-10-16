"""Lambda function to automatically initialize pgvector extension in RDS PostgreSQL.

This function is triggered after RDS instance creation and ensures the pgvector
extension is installed without requiring manual intervention.
"""

import json
import logging
import os
import sys
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Check if psycopg2 is available (provided via Lambda layer)
try:
    import psycopg2
except ImportError:
    logger.error("psycopg2 not available. Please add AWS Lambda PostgreSQL layer.")
    psycopg2 = None


def get_db_credentials(secret_arn: str) -> dict[str, str]:
    """Retrieve database credentials from Secrets Manager.

    Args:
        secret_arn: ARN of the secret containing DB credentials

    Returns:
        Dictionary with username, password, host, port, dbname
    """
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])

    return {
        "username": secret["username"],
        "password": secret["password"],
        "host": secret["host"],
        "port": secret.get("port", 5432),
        "dbname": secret.get("dbname", "postgres"),
    }


def initialize_pgvector(credentials: dict[str, str]) -> dict[str, Any]:
    """Initialize pgvector extension in PostgreSQL database.

    Args:
        credentials: Database connection credentials

    Returns:
        Result dictionary with status and message
    """
    if psycopg2 is None:
        return {
            "status": "error",
            "message": "psycopg2 not available in Lambda environment",
        }

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=credentials["host"],
            port=credentials["port"],
            user=credentials["username"],
            password=credentials["password"],
            dbname=credentials["dbname"],
            connect_timeout=10,
        )
        conn.autocommit = True

        cursor = conn.cursor()

        # Check if pgvector is already installed
        cursor.execute(
            "SELECT * FROM pg_extension WHERE extname = 'vector';"
        )
        existing = cursor.fetchone()

        if existing:
            logger.info("pgvector extension already installed")
            return {
                "status": "success",
                "message": "pgvector extension already installed",
                "action": "none",
            }

        # Create pgvector extension
        logger.info("Installing pgvector extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Verify installation
        cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        version = cursor.fetchone()

        cursor.close()
        conn.close()

        if version:
            logger.info(f"pgvector extension installed successfully: version {version[0]}")
            return {
                "status": "success",
                "message": f"pgvector extension installed (version {version[0]})",
                "action": "created",
                "version": version[0],
            }
        else:
            return {
                "status": "error",
                "message": "pgvector installation verification failed",
            }

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        return {
            "status": "error",
            "message": f"Database error: {str(e)}",
            "error_code": e.pgcode if hasattr(e, "pgcode") else None,
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
        }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler function.

    Args:
        event: Lambda event (can be CloudFormation custom resource or manual trigger)
        context: Lambda context

    Returns:
        Response dictionary
    """
    logger.info(f"Event: {json.dumps(event)}")

    # Get secret ARN from environment or event
    secret_arn = os.environ.get("DB_SECRET_ARN")

    if not secret_arn and "ResourceProperties" in event:
        # CloudFormation custom resource
        secret_arn = event["ResourceProperties"].get("SecretArn")

    if not secret_arn:
        logger.error("DB_SECRET_ARN not provided")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "DB_SECRET_ARN not provided"}),
        }

    try:
        # Get database credentials
        credentials = get_db_credentials(secret_arn)

        # Initialize pgvector
        result = initialize_pgvector(credentials)

        logger.info(f"Result: {json.dumps(result)}")

        return {
            "statusCode": 200 if result["status"] == "success" else 500,
            "body": json.dumps(result),
        }

    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
