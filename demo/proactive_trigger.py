"""
Simulates the PRIMARY demo path: a new test/pipeline failure "fires" (in a
real deployment this would be a dbt test failure webhook, an Airflow
on-failure callback, or a Great Expectations checkpoint failure), and the
agent automatically investigates against memory and posts the result --
nobody has to think to ask it anything.

Run:
    python demo/proactive_trigger.py "marketing_attribution dashboard showing 30% fewer conversions than last week, finance is asking questions"

If no argument is given, it cycles through a few canned "new" failures that
were deliberately phrased differently from anything in the ingested history,
to demonstrate semantic/graph matching beating keyword search.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cognee_layer.query import investigate

CANNED_NEW_FAILURES = [
    "finance_revenue_recognition totals look about 20% low this week and nobody changed anything we know of",
    "customer_360 Airflow job has been stuck for 40 minutes, way past normal runtime",
    "support seeing blank shipping_address on a bunch of customer_360 records since this morning",
]


def render_alert_card(symptom: str, recall_result: str) -> str:
    return (
        "\n" + "─" * 78 + "\n"
        f"  🔔  NEW FAILURE DETECTED\n"
        f"  {symptom}\n"
        + "─" * 78 + "\n"
        f"  🧠  PIPELINE MEMORY (auto-posted, no one asked):\n\n"
        f"{recall_result}\n"
        + "─" * 78 + "\n"
    )


async def handle_failure(symptom: str):
    result = await investigate(symptom)
    print(render_alert_card(symptom, result))


async def main():
    if len(sys.argv) > 1:
        await handle_failure(" ".join(sys.argv[1:]))
        return

    for symptom in CANNED_NEW_FAILURES:
        await handle_failure(symptom)


if __name__ == "__main__":
    asyncio.run(main())
