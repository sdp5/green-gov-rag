import os

import requests  # type: ignore[import-untyped]
from configs.documents_config import DOCUMENT_SOURCES

RAW_DIR = "data/raw"
os.makedirs(RAW_DIR, exist_ok=True)


def download_file(name, url):
    local_filename = os.path.join(RAW_DIR, f"{name}.pdf")
    response = requests.get(url)
    with open(local_filename, "wb") as f:
        f.write(response.content)
    print(f"✅ Downloaded: {local_filename}")


if __name__ == "__main__":
    for doc in DOCUMENT_SOURCES:
        download_file(doc["name"], doc["url"])
