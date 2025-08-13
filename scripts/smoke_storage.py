import os
import sys
from pprint import pprint

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from mcp_twotruths.storage import TableStorage  # type: ignore


def main():
    print("Using AzureWebJobsStorage:", bool(os.getenv("AzureWebJobsStorage")))
    store = TableStorage()

    host = "host@example.com"
    u1 = ("alice@example.com", "Alice")
    u2 = ("bob@example.com", "Bob")

    store.upsert_user(*u1)
    store.upsert_user(*u2)

    session = store.create_session(host)
    print("Session:", session)

    store.upsert_statements(session, u1[0], "I love cats", "I ran a marathon", "I've been to Mars", u1[1])
    store.upsert_statements(session, u2[0], "I play guitar", "I speak 4 languages", "I can fly unaided", u2[1])

    pr1 = store.create_presentation(session, u1[0])
    pr2 = store.create_presentation(session, u2[0])
    print("Presentation 1:")
    pprint(pr1)
    print("Presentation 2:")
    pprint(pr2)

    # Bob guesses Alice's lie is index 3
    store.cast_vote(session, voter_email=u2[0], target_email=u1[0], chosen_index=3)
    # Alice guesses Bob's lie is index 3
    store.cast_vote(session, voter_email=u1[0], target_email=u2[0], chosen_index=3)

    tally1 = store.tally_target(session, u1[0])
    tally2 = store.tally_target(session, u2[0])
    print("Tally for Alice:")
    pprint(tally1)
    print("Tally for Bob:")
    pprint(tally2)

    print("Scores:")
    pprint(store.list_scores(session))


if __name__ == "__main__":
    main()
