"""
Demonstrates the self-improvement loop: a "known fix" from memory gets
applied to a new occurrence, but this time it DOESN'T resolve the issue.
That outcome gets recorded as session feedback and bridged into the
permanent graph via improve() (Memify under the hood), so future recall()
calls down-weight that fix instead of recommending it again at full
confidence.

This follows Cognee's documented session -> improve() -> recall() pattern
(see docs.cognee.ai/guides/self-improvement-quickstart): feedback is
recorded as session memory, then improve(session_ids=[...]) bridges and
re-weights the permanent graph.

Run:
    python demo/feedback_loop.py
"""

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cognee_layer.config import configure_cognee, dataset_for_pipeline
from cognee_layer.query import investigate

PIPELINE = "marketing_attribution"


async def main():
    cognee = configure_cognee()
    session_id = f"feedback_{uuid.uuid4().hex[:8]}"

    print("STEP 1 -- Recall before feedback:")
    before = await investigate(
        "marketing_attribution job timing out, running way longer than usual"
    )
    print(before)

    print("\nSTEP 2 -- An engineer applies the 'known fix' from memory "
          "(add index / make incremental), but reports it did NOT fully "
          "resolve the slowdown this time. Recording that as session "
          "feedback...\n")
    await cognee.remember(
        "Follow-up on the marketing_attribution slow-job issue: the "
        "previously known fix (adding a clustering key and converting to "
        "an incremental model) was re-applied, but the job is still "
        "running 2x slower than baseline. The clustering-key fix should "
        "no longer be treated as a complete solution for this failure "
        "pattern -- there is likely a second, undiagnosed contributing "
        "factor.",
        dataset_name=dataset_for_pipeline(PIPELINE),
        session_id=session_id,
    )

    print("STEP 3 -- Bridging session feedback into permanent memory via "
          "improve() (Memify enrichment + edge re-weighting)...\n")
    await cognee.improve(dataset=dataset_for_pipeline(PIPELINE), session_ids=[session_id])

    print("STEP 4 -- Recall after improve():")
    after = await investigate(
        "marketing_attribution job timing out, running way longer than usual"
    )
    print(after)
    print(
        "\nExpected difference: the post-improve() answer should no longer "
        "present the clustering-key fix as a settled, fully-confirmed "
        "solution, and should mention the unresolved follow-up."
    )


if __name__ == "__main__":
    asyncio.run(main())
