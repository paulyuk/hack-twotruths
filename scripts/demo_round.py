import os
import sys
import random
from pprint import pprint

# Ensure src is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from mcp_twotruths.storage import TableStorage  # type: ignore

def play_round():
    # Ensure storage connection is set
    if not (os.getenv("AzureWebJobsStorage") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")):
        print("Warning: No AzureWebJobsStorage set. For local dev, run Azurite or set a real connection string.")

    store = TableStorage()

    # Register users
    players = [
        {"email": "alice@example.com", "alias": "Alice"},
        {"email": "bob@example.com", "alias": "Bob"},
        {"email": "carol@example.com", "alias": "Carol"},
    ]
    for p in players:
        store.upsert_user(p["email"], p["alias"])

    session_id = store.create_session(players[0]["email"])  # Alice as host
    print(f"Session created: {session_id}")

    # Statements (2 truths + 1 lie per player)
    sets = {
        "alice@example.com": ("I love cats", "I ran a marathon", "I have been to Mars"),
        "bob@example.com": ("I play guitar", "I speak 4 languages", "I can fly unaided"),
        "carol@example.com": ("I’ve met a president", "I hate pizza", "I collect stamps"),
    }
    for p in players:
        t1, t2, l1 = sets[p["email"]]
        store.upsert_statements(session_id, p["email"], t1, t2, l1, p["alias"])

    # Prepare presentations
    random.seed(42)
    for p in players:
        pr = store.create_presentation(session_id, p["email"])  # stores randomized order and lieIndex
        order = pr["order"].split(",")
        print(f"Presentation for {p['alias']} order: {order}")

    # Cast votes (naive random choices for demo)
    for voter in players:
        for target in players:
            if voter["email"] == target["email"]:
                continue
            choice = random.randint(1, 3)
            store.cast_vote(session_id, voter_email=voter["email"], target_email=target["email"], chosen_index=choice)

    # Tally and reveal
    print("\nReveal and Tally:")
    for p in players:
        tally = store.tally_target(session_id, p["email"])  # updates scores
        print(f"- {p['alias']} lie index: {tally['lieIndex']}")
        correct = sum(1 for r in tally["results"] if r["correct"])
        total = len(tally["results"])
        print(f"  Correct guesses: {correct}/{total}")

    # Scores
    print("\nScores:")
    scores = store.list_scores(session_id)
    pprint(sorted(scores, key=lambda e: (-int(e.get("score", 0)), e.get("email"))))


if __name__ == "__main__":
    play_round()
