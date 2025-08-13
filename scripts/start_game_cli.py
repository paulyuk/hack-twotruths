import os
import sys
from typing import List, Dict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from mcp_twotruths.storage import TableStorage  # type: ignore


def prompt(msg: str) -> str:
    try:
        return input(msg).strip()
    except EOFError:
        return ""


def collect_int(msg: str, min_val: int = 1, max_val: int | None = None) -> int:
    while True:
        s = prompt(msg)
        try:
            v = int(s)
            if v < min_val:
                raise ValueError()
            if max_val is not None and v > max_val:
                raise ValueError()
            return v
        except Exception:
            print(f"Please enter a number between {min_val}{' and ' + str(max_val) if max_val else ''}.")


def main():
    if not (os.getenv("AzureWebJobsStorage") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")):
        print("Warning: AzureWebJobsStorage is not set. For local dev, install/run Azurite or set a real connection string.")

    store = TableStorage()

    print("Two Truths and a Lie — Real Game")
    host_alias = prompt("Host alias: ")
    host_email = prompt("Host email: ")
    if not host_email:
        print("Host email is required.")
        sys.exit(1)
    store.upsert_user(host_email, host_alias or host_email)
    session_id = store.create_session(host_email)
    print(f"Session created: {session_id}\n")

    players: List[Dict[str, str]] = []
    n = collect_int("Number of players (including host): ", min_val=2)
    print("\nEnter player info (including host):")
    for i in range(n):
        alias = prompt(f" Player {i+1} alias: ")
        email = prompt(f" Player {i+1} email: ")
        if not email:
            print(" Email is required. Try again.")
            return
        store.upsert_user(email, alias or email)
        players.append({"alias": alias or email, "email": email})

    print("\nCollecting statements (2 truths and 1 lie) for each player.")
    for p in players:
        print(f"\n-- {p['alias']} --")
        t1 = prompt(" Truth 1: ")
        t2 = prompt(" Truth 2: ")
        l1 = prompt(" Lie 1: ")
        store.upsert_statements(session_id, p["email"], t1, t2, l1, p["alias"])

    print("\nPresenting statements and collecting votes...")
    for target in players:
        pr = store.create_presentation(session_id, target["email"])  # random order persisted
        st = store.get_statements(session_id, target["email"]) or {}
        order = pr.get("order", "").split(",")
        texts = []
        for k in order:
            if k == "truth1":
                texts.append(st.get("truth1", ""))
            elif k == "truth2":
                texts.append(st.get("truth2", ""))
            elif k == "lie1":
                texts.append(st.get("lie1", ""))
            else:
                texts.append("")

        print(f"\n== {target['alias']}'s statements ==")
        for i, txt in enumerate(texts, start=1):
            print(f" {i}. {txt}")

        for voter in players:
            if voter["email"] == target["email"]:
                continue
            choice = collect_int(f" {voter['alias']}, which one is the lie? (1-3): ", 1, 3)
            store.cast_vote(session_id, voter_email=voter["email"], target_email=target["email"], chosen_index=choice)

        tally = store.tally_target(session_id, target["email"])  # updates scores for correct guesses
        print(f" Reveal: Lie index is {tally['lieIndex']}")
        correct = sum(1 for r in tally["results"] if r["correct"])
        total = len(tally["results"])
        print(f" Correct guesses: {correct}/{total}")

    print("\nFinal Scores:")
    scores = store.list_scores(session_id)
    # Map emails to alias for display
    alias_map = {p["email"].lower(): p["alias"] for p in players}
    for s in sorted(scores, key=lambda e: (-int(e.get("score", 0)), e.get("email", ""))):
        email = s.get("email", "").lower()
        alias = alias_map.get(email, email)
        print(f" {alias}: {int(s.get('score', 0))}")


if __name__ == "__main__":
    main()
