"""
Secondary path: ad-hoc chat for an engineer who wants to dig deeper or ask
about something the proactive trigger wasn't pointed at. Uses the exact
same investigate()/recall() core as the proactive trigger -- this is
intentionally a thin shell, not a parallel implementation.

Run:
    python demo/chat_cli.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cognee_layer.query import ask


async def main():
    print("Pipeline Memory -- ask anything about past incidents.")
    print("(type 'exit' to quit)\n")
    while True:
        try:
            question = input("you> ").strip()
        except EOFError:
            break
        if not question or question.lower() in ("exit", "quit"):
            break
        answer = await ask(question)
        print(f"\nagent> {answer}\n")


if __name__ == "__main__":
    asyncio.run(main())
