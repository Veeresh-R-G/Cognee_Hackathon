"""
Thin wrapper around cognee.recall() that both the proactive trigger and the
ad-hoc chat path call into. Keeping this in one place means the proactive
path and the chat path are guaranteed to use the same graph traversal logic,
not two parallel re-implementations.

IMPORTANT: cognee.recall() does NOT return a plain string. It returns a
list of typed, discriminated entries (QA pairs, graph snippets, graph
context, session context, agent traces) -- see
cognee.modules.recall.types.RecallResponse. format_recall_result() below
unpacks that defensively into something printable/demo-able.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cognee_layer.config import configure_cognee, all_dataset_names


def format_recall_result(result) -> str:
    """
    Defensively flattens whatever mix of entry types recall() returns into
    a readable block of text. Prefers a synthesized QA-style answer if one
    is present; otherwise falls back to the raw graph/context snippets that
    were retrieved, which is still useful for the demo (you can literally
    show "here is the graph node it pulled").
    """
    if not result:
        return "(no memory matched this query yet -- has ingest.py been run?)"

    pieces = []
    for entry in result:
        source = getattr(entry, "source", None)
        answer = getattr(entry, "answer", None)
        text = getattr(entry, "text", None)
        content = getattr(entry, "content", None)

        if answer:
            pieces.append(answer)
        elif text:
            score = getattr(entry, "score", None)
            score_str = f" (score={score:.2f})" if isinstance(score, (int, float)) else ""
            pieces.append(f"[{source or 'graph'}{score_str}] {text}")
        elif content:
            pieces.append(f"[{source or 'context'}] {content}")

    if not pieces:
        return str(result)

    return "\n".join(pieces)


async def investigate(symptom_description: str) -> str:
    """
    Given a new, freshly-observed failure symptom (in whatever wording an
    engineer or an alerting system used), recall the closest matching past
    incident(s) from the knowledge graph, including root cause, fix, and
    owner -- even if the wording doesn't match the original incident at all.
    """
    cognee = configure_cognee()

    query = (
        f"A new pipeline issue was just observed: \"{symptom_description}\". "
        f"Has anything like this happened before? If so, what was the root "
        f"cause, what fix was applied, did the fix actually work, and who "
        f"owns the affected pipeline?"
    )

    result = await cognee.recall(query, datasets=all_dataset_names())
    return format_recall_result(result)


async def ask(question: str) -> str:
    """Generic ad-hoc question against the same memory (used by chat_cli.py)."""
    cognee = configure_cognee()
    result = await cognee.recall(question, datasets=all_dataset_names())
    return format_recall_result(result)
