# Two Truths and a Lie Agent: Ideal Prompt, Tools, and Azure Hosting

## Ideal System Prompt
You are a helpful, engaging, and funny agent that hosts a game of Two Truths and a Lie for multiple users. Your job is to:
- Register users (alias and email)
- Collect two truths and one lie from each user (in order: Truth 1, Truth 2, Lie 1)
- Encourage or clarify within 20 seconds if users are inactive/unclear
- Present each user’s randomized statements for group voting
- Collect votes on which statement is the lie
- Reveal the correct answer and keep score
- Keep emails private; be playful and encouraging
- Reference: https://parade.com/1185071/marynliles/two-truths-and-a-lie-ideas/

## MCP Tools (one server)
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

## Azure Hosting (BYO MCP on Functions)
- Host the MCP server as a custom handler on Azure Functions (Python 3.12).
- Use AzureWebJobsStorage (Table service) for persistence in a single table `twotruths`.
- Required files: `host.json`, `mcp-handler/function.json`, `local.settings.json`, `requirements.txt`, `main.py`.
- Entrypoint must bind to `FUNCTIONS_CUSTOMHANDLER_PORT` with `stateless_http=True`.
- Deployment: follow https://github.com/Azure-Samples/mcp-sdk-functions-hosting-python and BYO guide.

## Notes
- This repo includes scaffolding under `src/mcp_twotruths/*` and startup script `main.py`.
- Add timers/encouragement in the client/agent orchestration; tools provide storage and state.
- Consider APIM for OAuth-protected access per the sample if needed.

## GitHub tasks via MCP server
- For all GitHub operations (create repo, issues, PRs, labels, releases), use the GitHub MCP server rather than ad-hoc scripts.
- In VS Code, enable the GitHub MCP server and grant scopes for repo management.
- Keep repository and secret operations within the MCP toolchain for traceability and least-privilege access.
