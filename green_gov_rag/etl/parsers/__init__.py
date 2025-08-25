# parsers/__init__.py

from pathlib import Path

from .html_parser import parse_html
from .pdf_parser import parse_pdf

SUPPORTED_PARSERS = {
    ".pdf": parse_pdf,
    ".html": parse_html,
    ".htm": parse_html,
}


def get_parser(file_path: str):
    """
    Dispatcher function to get the right parser function
    based on file extension.

    Args:
        file_path (str): Path to the file.

    Returns:
        function: A parser function that accepts `file_path`
                  and returns extracted text.
    """
    ext = Path(file_path).suffix.lower()
    parser = SUPPORTED_PARSERS.get(ext)

    if not parser:
        raise ValueError(f"Unsupported file extension: {ext}")

    return parser


def parse_file(file_path: str) -> str:
    """
    Directly parse a file using the dispatcher.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: Extracted text content.
    """
    parser = get_parser(file_path)
    return parser(file_path)
