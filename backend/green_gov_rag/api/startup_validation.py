"""Startup validation for production safety.

Validates critical configuration and credentials before allowing
the application to start serving requests.
"""

from __future__ import annotations

import logging
import os
import sys

from green_gov_rag.config import settings

logger = logging.getLogger(__name__)


class StartupValidationError(Exception):
    """Raised when startup validation fails."""

    pass


def validate_llm_credentials() -> None:
    """Validate LLM provider credentials are configured.

    Raises:
        StartupValidationError: If credentials are missing in production
    """
    provider = settings.llm_provider.lower()
    is_production = settings.app_env.lower() == "production"
    skip_validation = os.getenv("SKIP_VALIDATION", "false").lower() == "true"

    # In production, always validate unless explicitly skipped
    if is_production and skip_validation:
        logger.warning(
            "⚠️  SKIP_VALIDATION=true in production - this is dangerous! "
            "LLM credentials will not be validated."
        )

    should_validate = is_production and not skip_validation

    # Check provider-specific credentials
    missing_creds = []

    if provider == "openai":
        if not settings.openai_api_key or settings.openai_api_key == "sk-your-key-here":
            missing_creds.append("OPENAI_API_KEY")

    elif provider == "azure":
        if not settings.azure_openai_api_key:
            missing_creds.append("AZURE_OPENAI_API_KEY")
        if not settings.azure_openai_endpoint:
            missing_creds.append("AZURE_OPENAI_ENDPOINT")
        if not settings.azure_openai_deployment:
            missing_creds.append("AZURE_OPENAI_DEPLOYMENT")

    elif provider == "bedrock":
        if not settings.bedrock_model_id:
            missing_creds.append("BEDROCK_MODEL_ID")
        # AWS credentials checked via boto3

    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            missing_creds.append("ANTHROPIC_API_KEY")

    # Handle missing credentials
    if missing_creds:
        error_msg = (
            f"LLM provider '{provider}' is missing required credentials:\n"
            f"  Missing: {', '.join(missing_creds)}\n\n"
            f"To fix this:\n"
            f"  1. Set the required environment variables\n"
            f"  2. Or update your .env file\n"
            f"  3. Or change LLM_PROVIDER to a configured provider\n"
        )

        if should_validate:
            # Production: hard fail
            error_msg += (
                "\n❌ APP_ENV=production requires valid LLM credentials.\n"
                "   Application will not start.\n"
            )
            raise StartupValidationError(error_msg)
        else:
            # Development: warn only
            logger.warning(
                f"⚠️  LLM credentials missing (APP_ENV={settings.app_env}):\n{error_msg}"
            )

    logger.info(f"✓ LLM provider '{provider}' credentials validated")


def test_llm_connectivity() -> None:
    """Perform smoke test of LLM connectivity.

    Raises:
        StartupValidationError: If LLM connectivity test fails in production
    """
    is_production = settings.app_env.lower() == "production"
    skip_validation = os.getenv("SKIP_VALIDATION", "false").lower() == "true"

    if skip_validation:
        logger.warning("⚠️  Skipping LLM connectivity test (SKIP_VALIDATION=true)")
        return

    # Only run smoke test in production or if explicitly enabled
    run_smoke_test = (
        is_production or os.getenv("TEST_LLM_ON_STARTUP", "false").lower() == "true"
    )

    if not run_smoke_test:
        logger.info("ℹ️  LLM connectivity test skipped (not production)")
        return

    try:
        from green_gov_rag.rag.llm_factory import get_llm

        logger.info("Testing LLM connectivity...")
        llm = get_llm()

        # Simple test query
        test_prompt = "Say 'OK' if you can read this."
        response = llm.invoke(test_prompt)

        # Check for valid response
        if not response or len(str(response).strip()) == 0:
            raise ValueError("LLM returned empty response")

        logger.info(
            f"✓ LLM connectivity test passed (provider: {settings.llm_provider})"
        )

    except Exception as e:
        error_msg = (
            f"LLM connectivity test failed:\n"
            f"  Provider: {settings.llm_provider}\n"
            f"  Model: {settings.llm_model}\n"
            f"  Error: {str(e)}\n\n"
            f"This usually indicates:\n"
            f"  - Invalid API credentials\n"
            f"  - Network connectivity issues\n"
            f"  - Invalid model name or endpoint\n"
        )

        if is_production:
            error_msg += (
                "\n❌ Production deployment requires working LLM.\n"
                "   Use SKIP_VALIDATION=true to bypass (NOT recommended).\n"
            )
            raise StartupValidationError(error_msg) from e
        else:
            logger.warning(
                f"⚠️  LLM connectivity test failed (non-production):\n{error_msg}"
            )


def validate_database() -> None:
    """Validate database connectivity.

    Raises:
        StartupValidationError: If database connection fails in production
    """
    is_production = settings.app_env.lower() == "production"
    skip_validation = os.getenv("SKIP_VALIDATION", "false").lower() == "true"

    if skip_validation and is_production:
        logger.warning("⚠️  Skipping database validation (SKIP_VALIDATION=true)")
        return

    try:
        from sqlalchemy import text

        from green_gov_rag.models.base import engine

        # Test database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        logger.info("✓ Database connectivity validated")

    except Exception as e:
        # Safely handle database URL display (hide credentials)
        db_url = settings.database_url or "Not configured"
        safe_db_url = db_url.split("@")[-1] if "@" in db_url else db_url

        error_msg = (
            f"Database connectivity test failed:\n"
            f"  Database URL: {safe_db_url}\n"
            f"  Error: {str(e)}\n"
        )

        if is_production:
            raise StartupValidationError(error_msg) from e
        else:
            logger.warning(
                f"⚠️  Database connectivity issue (non-production):\n{error_msg}"
            )


def run_startup_validation() -> None:
    """Run all startup validations.

    Raises:
        StartupValidationError: If any critical validation fails
        SystemExit: In production, exits the process on validation failure
    """
    logger.info("=" * 60)
    logger.info("Starting application validation...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info("=" * 60)

    try:
        # 1. Validate LLM credentials
        validate_llm_credentials()

        # 2. Test LLM connectivity
        test_llm_connectivity()

        # 3. Validate database
        validate_database()

        logger.info("=" * 60)
        logger.info("✓ All startup validations passed")
        logger.info("=" * 60)

    except StartupValidationError as e:
        logger.error("=" * 60)
        logger.error("❌ STARTUP VALIDATION FAILED")
        logger.error("=" * 60)
        logger.error(str(e))
        logger.error("=" * 60)

        # In production, exit immediately
        if settings.app_env.lower() == "production":
            logger.error("Production deployment aborted due to validation failure.")
            sys.exit(1)
        else:
            # In development, raise to allow debugging
            raise
