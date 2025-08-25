from bs4 import BeautifulSoup


def parse_html(file_path: str) -> str:
    """
    Parse and extract clean text content from an HTML file.

    Args:
        file_path (str): Path to the HTML file.

    Returns:
        str: Extracted and cleaned text from the HTML.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")

        # Remove script and style elements
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()

        # Extract visible text
        text = soup.get_text(separator=" ")

        # Clean up whitespace
        cleaned_text = " ".join(text.split())
        return cleaned_text

    except Exception as e:
        raise RuntimeError(f"Error parsing HTML file {file_path}: {e}")


# Example Usage
# from parsers.html_parser import parse_html
#
# if __name__ == "__main__":
#     file_path = "sample.html"
#     text = parse_html(file_path)
#     print(text[:500])  # Preview first 500 chars
