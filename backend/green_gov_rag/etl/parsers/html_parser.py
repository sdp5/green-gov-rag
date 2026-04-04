from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup


def parse_html(file_path: str) -> str:
    """Parse and extract clean text content from an HTML file.

    Args:
    ----
        file_path (str): Path to the HTML file.

    Returns:
    -------
        str: Extracted and cleaned text from the HTML.

    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")

        # Remove script and style elements
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()

        # Extract visible text
        text = soup.get_text(separator=" ")

        # Clean up whitespace
        return " ".join(text.split())

    except Exception as e:
        msg = f"Error parsing HTML file {file_path}: {e}"
        raise RuntimeError(msg)


def parse_html_structured(
    file_path: str,
    base_metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Parse HTML into structured format matching HierarchicalPDFParser output.

    Args:
        file_path: Path to the HTML file.
        base_metadata: Document-level metadata to merge into output.

    Returns:
        List with a single element containing the full text + metadata.
    """
    text = parse_html(file_path)
    meta: dict[str, Any] = dict(base_metadata) if base_metadata else {}
    meta["chunk_type"] = "paragraph"
    meta["chunk_id"] = 0
    return [{"content": text, "metadata": meta}]


# Example Usage
# from parsers.html_parser import parse_html
#
# if __name__ == "__main__":
#     file_path = "sample.html"
#     text = parse_html(file_path)
#     print(text[:500])  # Preview first 500 chars
