# Pipeline Memory

> AI-powered institutional memory for data pipeline incidents — built on [Cognee](https://github.com/topoteretes/cognee)'s hybrid graph-vector memory layer.

## The Problem

When a data pipeline breaks at 3am, the engineer debugging it almost never has the full picture. The root cause and fix for "this exact failure shape" may already exist — buried in a Slack thread, in someone's head, in a postmortem doc nobody thought to search. Wikis and runbooks don't solve this because **the bottleneck isn't writing — it's retrieval**. Nobody keyword-searches "blank shipping_address" and finds the upstream schema change that caused silent nulls three months ago on a completely different pipeline.

## The Solution

A memory layer where every resolved incident becomes a node in a causal graph:

```
pipeline → incident → symptom → root_cause → fix → owner
```

When a new failure fires, the agent traverses this graph and surfaces the closest historical precedent — **even when the surface wording is completely different**. Same fix confidence, same owner, zero re-investigation.

Two interfaces surface the same `recall()` core:

1. **Proactive (primary):** new failure fires → agent posts the matching precedent automatically, before anyone asks
2. **Web UI + chat:** ad-hoc investigation and pipeline management

## Demo

The output below shows the system matching `"blank shipping_address on customer_360"` to **INC-1002** on `inventory_snapshot` — a different pipeline, different column, different reporter — because the *causal structure is identical*: upstream schema change → renamed column → dbt model references old name → silent nulls.

```
🔔 NEW FAILURE DETECTED
support seeing blank shipping_address on customer_360 since this morning

🧠 PIPELINE MEMORY (auto-posted, no one asked):

Most Relevant Historical Incident: INC-1002 (inventory_snapshot)
  Symptom   : 40% null values in region_code suddenly appearing
  Root Cause: Upstream schema change in raw_warehouse_events renamed the source
              field, but the dbt model still referenced the old column name
  Fix       : Updated column reference (region_code_v1 → region_code),
              added not_null dbt test, added schema-change Slack alert
  Fix worked: ✅ Yes
  Owner     : Devika Rao, Supply Chain team
```

Keyword search on "blank shipping_address" → zero results. Graph traversal → exact match.

## How Cognee Powers This

All four lifecycle APIs are used with real design intent, not checkbox usage:

| API | Where | Why this design choice |
|---|---|---|
| `remember()` | `cognee_layer/ingest.py` | Each pipeline gets its own dataset (`pipeline_memory__<name>`), not one blob. This makes `forget()` surgically precise instead of all-or-nothing. Incidents are ingested as natural-language narratives so Cognee's entity/relationship extraction builds a rich causal graph (symptom → cause → fix → owner) rather than flat chunks. |
| `recall()` | `cognee_layer/query.py` | Queries across all pipeline datasets simultaneously. Cognee automatically routes between vector similarity (semantic matching of symptoms) and graph traversal (multi-hop cause→effect chains) — this is the hybrid that makes cross-pipeline pattern matching work without rewriting retrieval logic. |
| `improve()` | `demo/feedback_loop.py` | When a "known fix" is applied and doesn't fully resolve a recurrence, the outcome is recorded as session memory and bridged into the permanent graph via `improve(session_ids=[...])`. Edge weights are updated (alpha=0.1 per event), so fixes that repeatedly fail compound their uncertainty over time. |
| `forget()` | `demo/forget_demo.py` + UI | When a pipeline is decommissioned, its entire memory dataset is pruned cleanly. Without per-pipeline datasets, this would be impossible — `forget()` only operates at the dataset level. The UI exposes this as a one-click action per pipeline. |

## Project Structure

```
app.py                           FastAPI server + REST API
ui/index.html                    Single-file web UI (Slack-style alert cards)

data/
  generate_incident_history.py   Synthetic 6-month incident history generator
  incidents.json                 26 incidents across 5 pipelines, multiple owners
  pipelines.json                 Pipeline catalog (name, owner, team, upstream deps)
  dataset_names.json             Written by ingest.py, read by all demo scripts

cognee_layer/
  config.py     LLM/embedding config + dataset naming helpers
  ingest.py     Ingests incidents.json into Cognee via remember()
  query.py      recall() wrapper with typed-response unpacking

demo/
  proactive_trigger.py   Primary CLI demo: fire a failure, agent responds unprompted
  chat_cli.py            Ad-hoc Q&A against memory
  feedback_loop.py       improve()/Memify: session feedback → edge re-weighting
  forget_demo.py         forget(): prune a decommissioned pipeline's memory
```

## Setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...   # or set in .env
```

**No other services required.** Cognee defaults to fully local storage (SQLite + LanceDB + Kuzu graph). `fastembed` runs embeddings locally with no API key.

## Run Order

```bash
# Step 1 — Generate incident history (already done, re-run to regenerate)
python data/generate_incident_history.py

# Step 2 — Ingest into Cognee (~3-5 min, one LLM call per incident)
python cognee_layer/ingest.py

# Step 3 — Web UI (primary demo)
python app.py
# → open http://localhost:8000

# Step 4 — CLI demo (proactive trigger)
python demo/proactive_trigger.py
python demo/proactive_trigger.py "your own symptom here"

# Step 5 — Feedback loop
python demo/feedback_loop.py

# Step 6 — forget() demo
python demo/forget_demo.py
```

## Why Graph + Vector Hybrid Beats Plain RAG

| Approach | What it gets right | What it misses |
|---|---|---|
| Keyword search | Fast, exact matches | Misses same failure with different wording |
| Vector-only RAG | Semantic similarity | Can't traverse multi-hop cause→effect chains |
| **Graph + vector (Cognee)** | Semantic matching *and* causal traversal | — |

The graph traversal is what lets the system match `"blank shipping_address"` (customer_360, today) to `"40% null values in region_code"` (inventory_snapshot, 3 months ago): both lead to the same `upstream_schema_change → renamed_column → silent_null` causal path in the graph, even though the surface descriptions share zero keywords.

## AI Disclosure

Built with AI assistance (Claude) for code generation and documentation, as required by hackathon rules.

## Tech Stack

- **Memory layer:** [Cognee](https://github.com/topoteretes/cognee) 1.2.2 — graph + vector hybrid, fully local
- **LLM:** Anthropic Claude (via Cognee's LLM provider config)
- **Embeddings:** fastembed (BAAI/bge-small-en-v1.5) — local, no key
- **Storage:** SQLite (metadata) + LanceDB (vectors) + Kuzu/Ladybug (graph) — all local defaults
- **API:** FastAPI + uvicorn
- **UI:** Vanilla HTML/CSS/JS — zero framework dependencies
