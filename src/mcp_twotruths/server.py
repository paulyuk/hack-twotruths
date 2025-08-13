from __future__ import annotations

import asyncio
from typing import Dict, List

from mcp.server.fastmcp import FastMCP

from .storage import TableStorage


IDEAL_SYSTEM_PROMPT = (
    "You are a helpful, engaging, and funny agent that hosts a game of Two Truths and a Lie for multiple users. "
    "Register users (alias+email), collect Truth 1, Truth 2, Lie 1 in order, encourage within 20s if idle, present "
    "statements for group voting, collect votes, reveal the lie per user, and keep score. Keep emails private."
)


def create_server(port: int | None = None) -> FastMCP:
    storage = TableStorage()
    # Configure stateless HTTP transport per BYO Functions guidance
    kwargs = {}
    if port is not None:
        kwargs = {"stateless_http": True, "port": port}
    mcp = FastMCP("two-truths-agent", **kwargs)

    @mcp.tool()
    async def tt_register_user(email: str, alias: str) -> Dict:
        """Register or update a user profile by email and alias."""
        storage.upsert_user(email=email, alias=alias)
        return {"email": email.lower(), "alias": alias}

    @mcp.tool()
    async def tt_create_session(host_email: str) -> Dict:
        """Create a new session and return the session id."""
        session_id = storage.create_session(host_email)
        return {"sessionId": session_id, "status": "collecting"}

    @mcp.tool()
    async def tt_set_session_status(session_id: str, status: str) -> Dict:
        """Update session status: collecting|voting|reveal|ended."""
        storage.set_session_status(session_id, status)
        return {"sessionId": session_id, "status": status}

    @mcp.tool()
    async def tt_upsert_statements(session_id: str, email: str, alias: str, truth1: str, truth2: str, lie1: str) -> Dict:
        """Store a user's statements for a session."""
        storage.upsert_statements(session_id, email, truth1, truth2, lie1, alias)
        return {"ok": True}

    @mcp.tool()
    async def tt_list_statements(session_id: str) -> List[Dict]:
        """List all statements for a session (per user)."""
        return storage.list_statements(session_id)

    @mcp.tool()
    async def tt_prepare_presentation(session_id: str, target_email: str) -> Dict:
        """Create and return randomized presentation order and lie index (hidden)."""
        ent = storage.create_presentation(session_id, target_email)
        # return order for client presentation but do not reveal lie index
        order = ent.get("order", "").split(",")
        return {"target": target_email.lower(), "order": order}

    @mcp.tool()
    async def tt_cast_vote(session_id: str, voter_email: str, target_email: str, chosen_index: int) -> Dict:
        """Cast a vote for which statement (1,2,3) is the lie for target user."""
        if chosen_index not in (1, 2, 3):
            return {"ok": False, "error": "chosen_index must be 1, 2, or 3"}
        storage.cast_vote(session_id, voter_email, target_email, chosen_index)
        return {"ok": True}

    @mcp.tool()
    async def tt_list_votes_for_target(session_id: str, target_email: str) -> List[Dict]:
        """List votes cast for a specific target user (for tallying)."""
        return storage.list_votes_for_target(session_id, target_email)

    @mcp.tool()
    async def tt_tally_target(session_id: str, target_email: str) -> Dict:
        """Tally votes for a target user, update scores for correct guesses, and return results."""
        return storage.tally_target(session_id, target_email)

    @mcp.tool()
    async def tt_upsert_score(session_id: str, email: str, score: int) -> Dict:
        """Set or update a user's score for a session."""
        storage.upsert_score(session_id, email, score)
        return {"ok": True}

    @mcp.tool()
    async def tt_get_score(session_id: str, email: str) -> Dict:
        """Get a user's score for a session."""
        return {"email": email.lower(), "score": storage.get_score(session_id, email)}

    @mcp.tool()
    async def tt_list_scores(session_id: str) -> List[Dict]:
        """List all users' scores for a session."""
        return storage.list_scores(session_id)

    return mcp
