import os
import sys
import csv
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mcp_twotruths.storage import TableStorage  # type: ignore


def export_session(session_id: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    store = TableStorage()

    # Statements
    statements = store.list_statements(session_id)
    alias_by_email: Dict[str, str] = {}
    with (out_dir / f"session_{session_id}_statements.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["email", "alias", "truth1", "truth2", "lie1"])
        for s in statements:
            email = (s.get("email") or "").lower()
            alias = s.get("alias") or email
            alias_by_email[email] = alias
            w.writerow([email, alias, s.get("truth1", ""), s.get("truth2", ""), s.get("lie1", "")])

    # Votes (iterate all targets from statements)
    with (out_dir / f"session_{session_id}_votes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["target_email", "target_alias", "voter_email", "voter_alias", "choice", "correct", "lie_index"])
        for s in statements:
            target_email = (s.get("email") or "").lower()
            target_alias = s.get("alias") or target_email
            tally = store.tally_target(session_id, target_email)  # updates scores when correct
            lie_index = int(tally.get("lieIndex", 0))
            for r in tally.get("results", []):
                voter_email = (r.get("voter") or "").lower()
                voter_alias = alias_by_email.get(voter_email)
                if not voter_alias:
                    u = store.get_user(voter_email)
                    voter_alias = (u or {}).get("alias") or voter_email
                w.writerow([
                    target_email,
                    target_alias,
                    voter_email,
                    voter_alias,
                    int(r.get("choice", 0)),
                    bool(r.get("correct", False)),
                    lie_index,
                ])

    # Scores
    scores = store.list_scores(session_id)
    with (out_dir / f"session_{session_id}_scores.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["email", "alias", "score"])
        for s in scores:
            email = (s.get("email") or "").lower()
            alias = alias_by_email.get(email)
            if not alias:
                u = store.get_user(email)
                alias = (u or {}).get("alias") or email
            w.writerow([email, alias, int(s.get("score", 0))])

    print(f"Exported CSVs to {out_dir}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/export_session_csv.py <session_id> [output_dir]")
        sys.exit(1)

    session_id = sys.argv[1]
    out_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else ROOT / "exports"

    if not (os.getenv("AzureWebJobsStorage") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")):
        print("Warning: AzureWebJobsStorage is not set. For local, run Azurite or set a real connection string.")

    export_session(session_id, out_dir)


if __name__ == "__main__":
    main()
