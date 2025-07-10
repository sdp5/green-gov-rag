# Load YAML config and source files

import yaml

def load_documents_config(path="configs/documents_config.yml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)
