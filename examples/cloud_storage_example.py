#!/usr/bin/env python3
"""Example script demonstrating cloud-agnostic storage usage.

This example shows how to use the StorageClient abstraction layer
to work with AWS S3, Azure Blob Storage, or local filesystem storage
using the same code.
"""

import os
from pathlib import Path

from green_gov_rag.cloud import StorageClient
from green_gov_rag.cloud.config import get_storage_client


def main() -> None:
    """Demonstrate cloud storage operations."""
    # Method 1: Let the client auto-detect from environment
    print("=== Method 1: Auto-detect from CLOUD_PROVIDER env var ===")
    storage = get_storage_client()
    print(f"Using provider: {os.getenv('CLOUD_PROVIDER', 'local')}")

    # Method 2: Explicitly specify provider
    print("\n=== Method 2: Explicitly specify provider ===")
    storage_local = StorageClient(provider="local")
    print("Using provider: local")

    # Define container and key
    container = os.getenv("STORAGE_CONTAINER", "greengovrag-documents")
    test_file = "test_document.txt"
    test_key = "examples/test_document.txt"

    # Create a test file
    print(f"\n=== Creating test file: {test_file} ===")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("This is a test document for cloud storage.\n")
        f.write("It demonstrates the cloud-agnostic storage layer.\n")

    # Upload file
    print(f"\n=== Uploading {test_file} to {container}/{test_key} ===")
    storage.upload_file(test_file, container, test_key)
    print("✅ Upload successful")

    # Check if file exists
    print(f"\n=== Checking if {test_key} exists ===")
    exists = storage.file_exists(container, test_key)
    print(f"File exists: {exists}")

    # List files
    print(f"\n=== Listing files in {container} with prefix 'examples/' ===")
    files = storage.list_files(container, prefix="examples/")
    for file_key in files:
        print(f"  - {file_key}")

    # Download file
    download_path = "downloaded_test.txt"
    print(f"\n=== Downloading {test_key} to {download_path} ===")
    storage.download_file(container, test_key, download_path)
    print("✅ Download successful")

    # Verify contents
    print(f"\n=== Verifying downloaded file contents ===")
    with open(download_path, encoding="utf-8") as f:
        content = f.read()
        print(content)

    # Upload using file object
    print("\n=== Uploading using file object ===")
    test_key_2 = "examples/test_fileobj.txt"
    with open(test_file, "rb") as f:
        storage.upload_fileobj(f, container, test_key_2)
    print(f"✅ Uploaded to {test_key_2}")

    # Download using file object
    print("\n=== Downloading using file object ===")
    download_path_2 = "downloaded_fileobj.txt"
    with open(download_path_2, "wb") as f:
        storage.download_fileobj(container, test_key_2, f)
    print(f"✅ Downloaded to {download_path_2}")

    # Cleanup
    print("\n=== Cleaning up ===")
    storage.delete_file(container, test_key)
    storage.delete_file(container, test_key_2)
    print("✅ Deleted remote files")

    # Clean up local files
    Path(test_file).unlink(missing_ok=True)
    Path(download_path).unlink(missing_ok=True)
    Path(download_path_2).unlink(missing_ok=True)
    print("✅ Deleted local files")

    print("\n=== Example completed successfully! ===")


def multi_cloud_migration_example() -> None:
    """Example: Migrate files between cloud providers."""
    print("\n=== Multi-Cloud Migration Example ===")

    # Source: AWS
    source = StorageClient(provider="aws")
    source_container = "greengovrag-documents-aws"

    # Destination: Azure
    dest = StorageClient(provider="azure")
    dest_container = "greengovrag-documents-azure"

    # List files to migrate
    print(f"Listing files in source ({source_container})...")
    files_to_migrate = source.list_files(source_container, prefix="documents/")

    print(f"Found {len(files_to_migrate)} files to migrate")

    # Migrate each file
    for i, file_key in enumerate(files_to_migrate, 1):
        print(f"[{i}/{len(files_to_migrate)}] Migrating {file_key}...")

        # Download from source
        temp_file = f"/tmp/{Path(file_key).name}"
        source.download_file(source_container, file_key, temp_file)

        # Upload to destination
        dest.upload_file(temp_file, dest_container, file_key)

        # Clean up temp file
        Path(temp_file).unlink()

        print(f"✅ Migrated {file_key}")

    print("\n=== Migration completed! ===")


if __name__ == "__main__":
    # Set environment for demo (use local storage by default)
    if "CLOUD_PROVIDER" not in os.environ:
        os.environ["CLOUD_PROVIDER"] = "local"
        os.environ["LOCAL_STORAGE_PATH"] = "./data/storage"

    print("=" * 60)
    print("Cloud Storage Abstraction Layer Example")
    print("=" * 60)
    print(f"\nCurrent provider: {os.getenv('CLOUD_PROVIDER')}")
    print(f"Storage path/container: {os.getenv('STORAGE_CONTAINER', 'default')}")
    print()

    try:
        main()

        # Uncomment to test multi-cloud migration
        # Note: Requires valid AWS and Azure credentials
        # multi_cloud_migration_example()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
