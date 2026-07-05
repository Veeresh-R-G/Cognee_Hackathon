"""
Ingests the synthetic incident history into Cognee's permanent memory.

Each incident is written as a narrative paragraph rather than a flat JSON
dump on purpose: Cognee's graph extraction works off natural-language
relationships ("X caused Y", "owned by Z"), so the richer the prose, the
richer the resulting graph (pipeline -> incident -> symptom -> root cause ->
fix -> owner edges).

Design note on datasets: each PIPELINE gets its own Cognee dataset
(pipeline_memory__<pipeline_name>) rather than dumping everything into one
dataset. cognee.forget() only supports pruning at the dataset/data_id level
(no sub-graph "node_name" filter), so per-pipeline datasets are what make
"decommission this pipeline's memory" a clean, real operation later (see
demo/forget_demo.py) instead of a fake filter. recall() can still query
across all of them at once by passing the full list of dataset names.

Run (after exporting ANTHROPIC_API_KEY):
    python cognee_layer/ingest.py
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cognee_layer.config import configure_cognee, dataset_for_pipeline

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def incident_to_narrative(inc: dict) -> str:
    fix_status = (
        "This fix was confirmed to resolve the issue."
        if inc["fix_worked"]
        else "This fix was applied but later turned out to be incomplete -- the underlying issue resurfaced."
    )
    return (
        f"Incident {inc['incident_id']} occurred on {inc['occurred_at'][:10]} "
        f"on the '{inc['pipeline']}' pipeline, which is owned by {inc['owner']} "
        f"on the {inc['team']} team and depends on the upstream table '{inc['upstream_table']}'. "
        f"It was reported by {inc['reported_by']}. "
        f"Symptom: {inc['symptom']} "
        f"Root cause: {inc['root_cause']} "
        f"Fix applied: {inc['fix_applied']} "
        f"{fix_status}"
    )


async def main():
    cognee = configure_cognee()

    with open(os.path.join(DATA_DIR, "incidents.json")) as f:
        incidents = json.load(f)
    with open(os.path.join(DATA_DIR, "pipelines.json")) as f:
        pipelines = json.load(f)

    all_dataset_names = sorted({dataset_for_pipeline(p["name"]) for p in pipelines})
    print(f"Ingesting {len(incidents)} incidents across {len(all_dataset_names)} "
          f"per-pipeline datasets...")

    for inc in incidents:
        narrative = incident_to_narrative(inc)
        dataset_name = dataset_for_pipeline(inc["pipeline"])
        await cognee.remember(narrative, dataset_name=dataset_name)
        print(f"  remembered {inc['incident_id']} -> dataset '{dataset_name}'")

    # Save the dataset list so query.py / demo scripts know what to recall across
    with open(os.path.join(DATA_DIR, "dataset_names.json"), "w") as f:
        json.dump(all_dataset_names, f, indent=2)

    print(f"\nDone. Dataset names written to data/dataset_names.json.")
    print("Run demo/proactive_trigger.py to test recall against this memory.")


if __name__ == "__main__":
    asyncio.run(main())

