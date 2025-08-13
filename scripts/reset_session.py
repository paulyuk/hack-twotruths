import os
import sys
from pprint import pprint

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from mcp_twotruths.storage import TableStorage  # type: ignore


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/reset_session.py <session_id>")
        sys.exit(1)

    session_id = sys.argv[1]

    if not (os.getenv("AzureWebJobsStorage") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")):
        print("Warning: AzureWebJobsStorage is not set. For local dev, install/run Azurite or set a real connection string.")

    store = TableStorage()
    result = store.delete_session(session_id)
    print("Deleted entities:", result["deleted"])
    if result["errors"]:
        print("Errors:")
        pprint(result["errors"])


if __name__ == "__main__":
    main()
