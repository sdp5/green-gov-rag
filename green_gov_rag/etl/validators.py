# (Optional) Manual checks

import os
from pathlib import Path

def validate_file_exists(file_path: str) -> bool:
    """
    Checks if a given file exists.
    """
    return Path(file_path).exists()

def validate_pdf(file_path: str) -> bool:
    """
    Basic validation to check if a file is a PDF.
    """
    if not validate_file_exists(file_path):
        return False
    return file_path.lower().endswith(".pdf")

def validate_html(file_path: str) -> bool:
    """
    Basic validation to check if a file is an HTML document.
    """
    if not validate_file_exists(file_path):
        return False
    return file_path.lower().endswith((".html", ".htm"))

def validate_metadata(document: dict) -> bool:
    """
    Ensure required metadata fields are present.
    """
    required_fields = ["title", "jurisdiction", "category", "topic", "region", "sovereign"]
    return all(field in document for field in required_fields)

if __name__ == "__main__":
    # Example usage
    sample_file = "data/raw/demo.pdf"
    print("PDF valid:", validate_pdf(sample_file))
