"""
Central Cognee configuration for the Pipeline Memory project.

Design choice: LLM = Anthropic (you already have a key), embeddings = fastembed
(runs 100% locally, no key, no extra cost). Vector/graph/relational stores all
stay on Cognee's bundled local defaults (LanceDB / Kuzu-compatible / SQLite) --
zero servers to stand up for a 3-day hackathon build.

Set ANTHROPIC_API_KEY in your shell or a .env file before importing this
module (Cognee reads .env at import time).
"""

import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def dataset_for_pipeline(pipeline_name: str) -> str:
    return f"pipeline_memory__{pipeline_name}"


def all_dataset_names() -> list:
    """
    Reads the dataset list written by ingest.py. Run ingest.py at least once
    before calling this.
    """
    import json
    path = os.path.join(DATA_DIR, "dataset_names.json")
    if not os.path.exists(path):
        raise RuntimeError(
            "data/dataset_names.json not found -- run cognee_layer/ingest.py first."
        )
    with open(path) as f:
        return json.load(f)


def configure_cognee():
    import cognee

    # LLM provider
    cognee.config.set("llm_provider", "anthropic")
    cognee.config.set("llm_model", "anthropic/claude-sonnet-4-6")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it before running, e.g.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
        )
    cognee.config.set("llm_api_key", api_key)

    # Embeddings -- local, no key required
    cognee.config.set("embedding_provider", "fastembed")
    cognee.config.set("embedding_model", "BAAI/bge-small-en-v1.5")
    cognee.config.set("embedding_dimensions", 384)

    return cognee
