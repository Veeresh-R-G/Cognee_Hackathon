"""
Demonstrates forget() -- the fourth lifecycle API. Real scenario: a pipeline
gets decommissioned/replaced (e.g. "inventory_snapshot" gets rebuilt from
scratch on a new stack), and its old incident history is no longer relevant
context for recall -- worse, keeping it around risks the agent suggesting
fixes for a system that no longer exists.

NOTE ON THE REAL API: cognee.forget() prunes at the dataset / data_id level
-- there is no sub-graph "delete just this node" filter in the installed
version (verified against the live signature: forget(*, data_id=None,
dataset=None, dataset_id=None, everything=False, memory_only=False)).
That's exactly why ingest.py gives each pipeline its own Cognee dataset
(pipeline_memory__<pipeline_name>): it turns "surgically prune one
pipeline's memory" into a clean forget(dataset=...) call instead of
something the API can't actually do.

Run:
    python demo/forget_demo.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cognee_layer.config import configure_cognee, dataset_for_pipeline, all_dataset_names
from cognee_layer.query import format_recall_result

DECOMMISSIONED_PIPELINE = "inventory_snapshot"


async def main():
    cognee = configure_cognee()
    target_dataset = dataset_for_pipeline(DECOMMISSIONED_PIPELINE)
    question = "What incidents have happened on inventory_snapshot, and what were the fixes?"

    print(f"BEFORE forget() -- querying dataset '{target_dataset}':")
    before = await cognee.recall(question, datasets=[target_dataset])
    print(format_recall_result(before))

    print(f"\nPruning '{DECOMMISSIONED_PIPELINE}' (decommissioned pipeline) "
          f"via forget(dataset='{target_dataset}')...\n")
    await cognee.forget(dataset=target_dataset)

    remaining = [d for d in all_dataset_names() if d != target_dataset]
    print(f"AFTER forget() -- querying the SAME question across the "
          f"{len(remaining)} remaining pipeline datasets "
          f"(inventory_snapshot's dataset is gone):")
    after = await cognee.recall(question, datasets=remaining)
    print(format_recall_result(after))
    print(
        "\nExpected difference: the 'before' answer cites specific "
        "inventory_snapshot incidents and fixes; the 'after' answer should "
        "have nothing to say about inventory_snapshot at all, because that "
        "dataset no longer exists in memory."
    )


if __name__ == "__main__":
    asyncio.run(main())
