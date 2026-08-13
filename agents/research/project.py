import json
from pathlib import Path


def save_json(path, data):
    """
    Save a dictionary as JSON.
    """

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )