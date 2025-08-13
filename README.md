# Two Truths and a Lie MCP Server (Azure Functions BYO)

This project hosts a Model Context Protocol (MCP) server that provides tools for running a multiplayer "Two Truths and a Lie" game. It uses Azure Functions (custom handler) to host a bring-your-own (BYO) MCP server and Azure Table Storage via the AzureWebJobsStorage connection for persistence.

## What’s included
- MCP tools for user registration, sessions, statements collection, voting, tallying, and scores
- Azure Table Storage-backed persistence using the same AzureWebJobsStorage account
- Azure Functions custom handler artifacts (host.json, mcp-handler/function.json, local.settings.json)
- Ready to deploy with Azure Developer CLI (azd) following the sample repo

## MCP Tools
- tt_register_user(email, alias)
- tt_create_session(host_email)
- tt_set_session_status(session_id, status)
- tt_upsert_statements(session_id, email, alias, truth1, truth2, lie1)
- tt_list_statements(session_id)
- tt_prepare_presentation(session_id, target_email)
- tt_cast_vote(session_id, voter_email, target_email, chosen_index)
- tt_list_votes_for_target(session_id, target_email)
- tt_tally_target(session_id, target_email)
- tt_upsert_score(session_id, email, score)
- tt_get_score(session_id, email)
- tt_list_scores(session_id)

## Run locally
Prereqs: Python 3.12, Azure Functions Core Tools, VS Code with Azure Functions extension.

1. Create a venv and install deps:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. (Optional) Quick demo of storage and game flow (no Functions host needed):
```bash
python scripts/demo_round.py
```
3. Start Functions host (custom handler):
```bash
func start
```
4. Add a local MCP server in VS Code (Command Palette: MCP: Add server → HTTP) with URL:
```
http://0.0.0.0:7071/mcp
```
5. Start the server from the MCP view in VS Code.

### Start a real interactive game (CLI)
Run an actual game round in your terminal using the storage backend:
```bash
python scripts/start_game_cli.py
```

### Manage sessions
- List sessions (meta rows):
```python
from src.mcp_twotruths.storage import TableStorage
s = TableStorage()
print(s.list_sessions())
```

- Reset (delete) a session:
```bash
python scripts/reset_session.py <session_id>
```

### Export results to CSV
Write statements, votes, and scores to CSV files:
```bash
python scripts/export_session_csv.py <session_id>  # defaults to ./exports
python scripts/export_session_csv.py <session_id> ./my-exports
```

## Deploy
Follow the BYO guide in the sample repo:
- https://github.com/Azure-Samples/mcp-sdk-functions-hosting-python
- https://github.com/Azure-Samples/mcp-sdk-functions-hosting-python/blob/main/BYOServer.md

Key steps (summary):
- Create a Function App (Flex Consumption, Python 3.12)
- Add app setting:
```
PYTHONPATH=/home/site/wwwroot/.python_packages/lib/site-packages
```
- Deploy from VS Code: Azure Functions: Deploy to Function App
- Connect using remote MCP config in `.vscode/mcp.json` and add header `x-functions-key`

## Storage
- Uses the AzureWebJobsStorage connection string.
- Single table `twotruths` with logical partitioning:
  - Users: PartitionKey="users", RowKey=email
  - Sessions: PartitionKey=sessionId, RowKey="meta"
  - Statements: PartitionKey=sessionId, RowKey="st:{email}"
  - Presentations: PartitionKey=sessionId, RowKey="pr:{email}"
  - Votes: PartitionKey=sessionId, RowKey="vt:{voter}:{target}"
  - Scores: PartitionKey=sessionId, RowKey="sc:{email}"

## Notes
- Keep emails private when presenting to players.
- Add humor and encouragement messages on client side logic/timing (20s reminders).
- Consider APIM for OAuth-protected access per sample if needed.
