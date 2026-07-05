"""
Generates a synthetic-but-realistic 6-month incident history for a fictional
data platform ("Northwind Analytics"). This stands in for the real Slack
threads / postmortem docs / dbt test failures an actual data org would feed
into Cognee. Each incident is written the way a human would actually write
it -- inconsistent terminology, partial info, different authors -- on purpose,
because that's what makes the "graph beats keyword search" demo convincing.

Run: python generate_incident_history.py
Output: data/incidents.json (list of incident records) + data/pipelines.json
"""

import json
import os
import random
from datetime import datetime, timedelta

random.seed(42)

PIPELINES = [
    {"name": "orders_fact", "owner": "Priya Nair", "team": "Revenue Analytics",
     "upstream": ["raw_orders", "raw_customers"], "tool": "dbt + Snowflake"},
    {"name": "customer_360", "owner": "Marcus Lee", "team": "Growth",
     "upstream": ["orders_fact", "support_tickets", "marketing_events"], "tool": "dbt + Snowflake"},
    {"name": "inventory_snapshot", "owner": "Devika Rao", "team": "Supply Chain",
     "upstream": ["raw_warehouse_events"], "tool": "Airflow + dbt"},
    {"name": "marketing_attribution", "owner": "Tom Becker", "team": "Growth",
     "upstream": ["marketing_events", "orders_fact"], "tool": "Airflow + Spark"},
    {"name": "finance_revenue_recognition", "owner": "Priya Nair", "team": "Finance Eng",
     "upstream": ["orders_fact", "refunds_table"], "tool": "dbt + Snowflake"},
]

# Each "incident archetype" defines a symptom -> cause -> fix chain we will
# vary and reuse, because in real orgs the SAME underlying failure mode
# recurs across different pipelines and different surface symptoms.
ARCHETYPES = [
    {
        "symptom_templates": [
            "{pipeline} showing {pct}% null values in the {col} column since {time}",
            "Null spike in {col} on {pipeline}, started around {time}",
            "Customers reporting blank {col} field in the {pipeline} dashboard",
        ],
        "cause": "An upstream schema change in {upstream_table} renamed/deprecated the source field feeding {col}, but the dbt model for {pipeline} still references the old column name, so the join silently returns null instead of failing.",
        "fix": "Updated the {pipeline} dbt model to reference the renamed column ({old_col} -> {new_col}), added a not_null dbt test on {col}, and added a schema-change Slack alert on {upstream_table}.",
        "cols": ["customer_email", "region_code", "shipping_address", "discount_pct", "channel_id"],
    },
    {
        "symptom_templates": [
            "{pipeline} run failed at {time} with a duplicate key / primary key violation",
            "dbt test 'unique' failing on {pipeline}.{col} since the {time} run",
            "Row count for {pipeline} jumped {pct}% overnight with no corresponding source volume change",
        ],
        "cause": "A backfill job for {upstream_table} was re-run without a delete-before-insert step, so the {time} window of records got inserted twice into {pipeline}, breaking the uniqueness assumption on {col}.",
        "fix": "Added an idempotent MERGE (instead of INSERT) in the {pipeline} load step, and added a row-count anomaly test that compares against a 7-day rolling average before the backfill window.",
        "cols": ["order_id", "event_id", "ticket_id", "transaction_id"],
    },
    {
        "symptom_templates": [
            "{pipeline} numbers don't reconcile with {upstream_table} -- off by roughly {pct}%",
            "Finance flagged a discrepancy between {pipeline} and the source system, around {pct}% variance",
            "{pipeline} totals dropped {pct}% week-over-week with no business explanation",
        ],
        "cause": "A metric definition change made 3 sprints ago to {upstream_table} (a new business rule for what counts as a 'completed' record) was never propagated to the {pipeline} model, so it's still using the old filter logic and silently undercounting.",
        "fix": "Aligned the {pipeline} filter logic with the updated {upstream_table} business rule, and added an inline dbt model comment + a `metric_definition_version` column so future changes are tracked instead of tribal knowledge.",
        "cols": ["completed_orders", "active_customers", "recognized_revenue"],
    },
    {
        "symptom_templates": [
            "{pipeline} job timing out / running 3-4x longer than usual since {time}",
            "Airflow DAG for {pipeline} stuck in 'running' state past its SLA",
            "{pipeline} compute cost spiked noticeably starting {time}",
        ],
        "cause": "A recent change added an unindexed join against {upstream_table}, which used to be small but has grown past the point where the warehouse can do a full scan efficiently within the existing warehouse size.",
        "fix": "Added a clustering key / index on the join column in {upstream_table}, and split the {pipeline} model into an incremental model instead of a full rebuild on every run.",
        "cols": [],
    },
    {
        "symptom_templates": [
            "{pipeline} failing every {weekday} morning, same error each time",
            "Recurring failure on {pipeline} -- this is the {nth} time this exact error has shown up",
        ],
        "cause": "{upstream_table} has a scheduled maintenance/vacuum window on {weekday} mornings that briefly locks the table; {pipeline} isn't configured to retry on lock-timeout errors, so the whole run fails instead of waiting and retrying.",
        "fix": "Added retry-with-backoff logic to the {pipeline} extraction step specifically for lock-timeout errors, and moved the {pipeline} schedule to start 30 minutes after the maintenance window instead of overlapping it.",
        "cols": [],
    },
]

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

REPORTERS = ["Priya Nair", "Marcus Lee", "Devika Rao", "Tom Becker", "Anjali Mehta",
             "on-call rotation (pager)", "Slack #data-alerts bot", "a downstream BI analyst"]


def random_time_ago(days_min, days_max):
    dt = datetime(2026, 6, 29) - timedelta(days=random.randint(days_min, days_max),
                                            hours=random.randint(0, 23))
    return dt


def build_incident(idx, archetype, pipeline, recurrence_count=1):
    upstream_table = random.choice(pipeline["upstream"])
    col = random.choice(archetype["cols"]) if archetype["cols"] else ""
    pct = random.choice([8, 12, 15, 18, 22, 27, 31, 40])
    weekday = random.choice(WEEKDAYS)
    occurred_at = random_time_ago(3, 185)
    time_str = occurred_at.strftime("%b %d")

    symptom = random.choice(archetype["symptom_templates"]).format(
        pipeline=pipeline["name"], pct=pct, col=col, time=time_str,
        upstream_table=upstream_table, weekday=weekday, nth="3rd" if recurrence_count > 1 else "1st",
    )
    cause = archetype["cause"].format(
        pipeline=pipeline["name"], pct=pct, col=col, time=time_str,
        upstream_table=upstream_table, weekday=weekday,
        old_col=f"{col}_v1" if col else "n/a", new_col=col if col else "n/a",
    )
    fix = archetype["fix"].format(
        pipeline=pipeline["name"], pct=pct, col=col, time=time_str,
        upstream_table=upstream_table, weekday=weekday,
        old_col=f"{col}_v1" if col else "n/a", new_col=col if col else "n/a",
    )

    return {
        "incident_id": f"INC-{1000 + idx}",
        "pipeline": pipeline["name"],
        "owner": pipeline["owner"],
        "team": pipeline["team"],
        "upstream_table": upstream_table,
        "occurred_at": occurred_at.isoformat(),
        "reported_by": random.choice(REPORTERS),
        "symptom": symptom,
        "root_cause": cause,
        "fix_applied": fix,
        "fix_worked": random.random() > 0.12,  # ~12% of "known fixes" later turned out incomplete
        "archetype_id": ARCHETYPES.index(archetype),
    }


def main():
    incidents = []
    idx = 0
    # Make sure a few archetypes genuinely RECUR on different pipelines with
    # different wording -- this is the whole point of the demo.
    for archetype in ARCHETYPES:
        recurrence = random.randint(2, 4)
        chosen_pipelines = random.sample(PIPELINES, k=min(recurrence, len(PIPELINES)))
        for rec_count, pipeline in enumerate(chosen_pipelines, start=1):
            incidents.append(build_incident(idx, archetype, pipeline, rec_count))
            idx += 1

    # Add some extra one-off incidents for volume/realism
    for _ in range(10):
        archetype = random.choice(ARCHETYPES)
        pipeline = random.choice(PIPELINES)
        incidents.append(build_incident(idx, archetype, pipeline))
        idx += 1

    incidents.sort(key=lambda i: i["occurred_at"])

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, "incidents.json"), "w") as f:
        json.dump(incidents, f, indent=2)
    with open(os.path.join(out_dir, "pipelines.json"), "w") as f:
        json.dump(PIPELINES, f, indent=2)

    print(f"Generated {len(incidents)} incidents across {len(PIPELINES)} pipelines.")
    print(f"-> {os.path.join(out_dir, 'incidents.json')}")
    print(f"-> {os.path.join(out_dir, 'pipelines.json')}")


if __name__ == "__main__":
    main()
