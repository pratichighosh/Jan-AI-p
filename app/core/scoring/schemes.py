import json
import os
from functools import lru_cache
from typing import Dict, Any

# Path to app/schemes directory
SCHEMES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "schemes",
)


@lru_cache(maxsize=32)
def load_scheme_config(scheme_id: str) -> Dict[str, Any]:
    """
    Load scheme config JSON by scheme_id (e.g. 'pm-kisan').

    Maps 'pm-kisan' -> 'pm_kisan.json'
    """
    normalized_id = scheme_id.replace("-", "_")
    filename = f"{normalized_id}.json"
    path = os.path.join(SCHEMES_DIR, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Scheme config not found for id={scheme_id} (file={filename}): {path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_scheme_weights(scheme_id: str) -> Dict[str, float]:
    cfg = load_scheme_config(scheme_id)
    # default weights if missing
    return cfg.get(
        "weights",
        {"fields_complete": 0.6, "docs_present": 0.3, "validation_pass": 0.1},
    )


def get_required_fields(scheme_id: str):
    cfg = load_scheme_config(scheme_id)
    return cfg.get("required_fields", [])


def get_required_documents(scheme_id: str):
    cfg = load_scheme_config(scheme_id)
    return cfg.get("required_documents", [])
