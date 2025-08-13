from __future__ import annotations

import os
import uuid
from typing import Dict, List, Optional, Tuple
import random

from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableClient


class TableStorage:
    """
    Minimal Table Storage wrapper using the AzureWebJobsStorage connection string.
    Tables:
      - Users: PartitionKey="users", RowKey=email
      - Sessions: PartitionKey=sessionId, RowKey="meta"
      - Statements: PartitionKey=sessionId, RowKey=f"st:{email}"
    - Votes: PartitionKey=sessionId, RowKey=f"vt:{voterEmail}:{targetEmail}"
      - Scores: PartitionKey=sessionId, RowKey=f"sc:{email}"
    - Presentations: PartitionKey=sessionId, RowKey=f"pr:{targetEmail}"
    """

    def __init__(self, table_name: str = "twotruths") -> None:
        conn = os.getenv("AzureWebJobsStorage") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn:
            raise RuntimeError("AzureWebJobsStorage connection string not found in environment")
        self._client = TableClient.from_connection_string(conn, table_name=table_name)
        try:
            self._client.create_table()
        except Exception:
            # table may already exist
            pass

    # Users
    def upsert_user(self, email: str, alias: str) -> None:
        entity = {
            "PartitionKey": "users",
            "RowKey": email.lower(),
            "alias": alias,
        }
        self._client.upsert_entity(entity)

    def get_user(self, email: str) -> Optional[Dict]:
        try:
            return self._client.get_entity("users", email.lower())
        except Exception:
            return None

    # Sessions
    def create_session(self, host_email: str) -> str:
        session_id = str(uuid.uuid4())
        entity = {
            "PartitionKey": session_id,
            "RowKey": "meta",
            "host": host_email.lower(),
            "status": "collecting",
        }
        self._client.upsert_entity(entity)
        return session_id

    def set_session_status(self, session_id: str, status: str) -> None:
        ent = self._client.get_entity(session_id, "meta")
        ent["status"] = status
        self._client.upsert_entity(ent)

    def get_session(self, session_id: str) -> Optional[Dict]:
        try:
            return self._client.get_entity(session_id, "meta")
        except Exception:
            return None

    def list_sessions(self) -> List[Dict]:
        """List all sessions by querying meta rows across partitions."""
        # Query all rows with RowKey == 'meta' to discover sessions
        return list(self._client.query_entities("RowKey eq 'meta'"))

    def delete_session(self, session_id: str) -> Dict:
        """Delete all entities for a given session partition (meta, statements, votes, presentations, scores)."""
        deleted = 0
        errors: List[str] = []
        # Enumerate all entities with the session's PartitionKey
        try:
            pager = self._client.list_entities(query_filter=f"PartitionKey eq '{session_id}'")
        except TypeError:
            # Fallback for older SDKs
            pager = self._client.query_entities(f"PartitionKey eq '{session_id}'")
        for ent in pager:
            pk = ent["PartitionKey"]
            rk = ent["RowKey"]
            try:
                self._client.delete_entity(partition_key=pk, row_key=rk)
                deleted += 1
            except Exception as e:
                errors.append(f"{rk}: {e}")
        return {"sessionId": session_id, "deleted": deleted, "errors": errors}

    # Statements
    def upsert_statements(self, session_id: str, email: str, truth1: str, truth2: str, lie1: str, alias: str) -> None:
        entity = {
            "PartitionKey": session_id,
            "RowKey": f"st:{email.lower()}",
            "email": email.lower(),
            "alias": alias,
            "truth1": truth1,
            "truth2": truth2,
            "lie1": lie1,
        }
        self._client.upsert_entity(entity)

    def list_statements(self, session_id: str) -> List[Dict]:
        # Use lexicographic range for RowKey prefix 'st:'
        return list(
            self._client.query_entities(
                f"PartitionKey eq '{session_id}' and RowKey ge 'st:' and RowKey lt 'st;'"
            )
        )

    def get_statements(self, session_id: str, email: str) -> Optional[Dict]:
        try:
            return self._client.get_entity(session_id, f"st:{email.lower()}")
        except Exception:
            return None

    # Presentation (randomized order per target)
    def get_presentation(self, session_id: str, target_email: str) -> Optional[Dict]:
        try:
            return self._client.get_entity(session_id, f"pr:{target_email.lower()}")
        except Exception:
            return None

    def create_presentation(self, session_id: str, target_email: str) -> Dict:
        st = self.get_statements(session_id, target_email)
        if not st:
            raise ValueError("No statements for target user")

        # Build items and shuffle once; persist order
        items = [
            {"kind": "truth1", "text": st.get("truth1", "")},
            {"kind": "truth2", "text": st.get("truth2", "")},
            {"kind": "lie1", "text": st.get("lie1", "")},
        ]
        random.shuffle(items)
        order = ",".join(i["kind"] for i in items)
        lie_index = next((idx + 1 for idx, i in enumerate(items) if i["kind"] == "lie1"), 0)
        ent = {
            "PartitionKey": session_id,
            "RowKey": f"pr:{target_email.lower()}",
            "target": target_email.lower(),
            "order": order,
            "lieIndex": lie_index,
        }
        self._client.upsert_entity(ent)
        return ent

    # Votes
    def cast_vote(self, session_id: str, voter_email: str, target_email: str, chosen_index: int) -> None:
        entity = {
            "PartitionKey": session_id,
            "RowKey": f"vt:{voter_email.lower()}:{target_email.lower()}",
            "voter": voter_email.lower(),
            "target": target_email.lower(),
            "choice": int(chosen_index),  # 1,2,3 (index of lie guess)
        }
        self._client.upsert_entity(entity)

    def list_votes_for_target(self, session_id: str, target_email: str) -> List[Dict]:
        # Filter by RowKey prefix 'vt:' via range and target property
        return list(
            self._client.query_entities(
                f"PartitionKey eq '{session_id}' and RowKey ge 'vt:' and RowKey lt 'vt;' and target eq '{target_email.lower()}'"
            )
        )

    def tally_target(self, session_id: str, target_email: str) -> Dict:
        pr = self.get_presentation(session_id, target_email)
        if not pr:
            raise ValueError("Presentation not found; call create_presentation first")
        lie_index = int(pr.get("lieIndex", 0))
        votes = self.list_votes_for_target(session_id, target_email)
        results: List[Dict] = []
        for v in votes:
            correct = int(v.get("choice", 0)) == lie_index
            results.append({
                "voter": v.get("voter"),
                "choice": int(v.get("choice", 0)),
                "correct": correct,
            })
            if correct:
                # increment score by 1
                email = v.get("voter").lower()
                cur = self.get_score(session_id, email)
                self.upsert_score(session_id, email, cur + 1)
        return {"target": target_email.lower(), "lieIndex": lie_index, "results": results}

    # Scores
    def upsert_score(self, session_id: str, email: str, score: int) -> None:
        entity = {
            "PartitionKey": session_id,
            "RowKey": f"sc:{email.lower()}",
            "email": email.lower(),
            "score": int(score),
        }
        self._client.upsert_entity(entity)

    def get_score(self, session_id: str, email: str) -> int:
        try:
            ent = self._client.get_entity(session_id, f"sc:{email.lower()}")
            return int(ent.get("score", 0))
        except Exception:
            return 0

    def list_scores(self, session_id: str) -> List[Dict]:
        # Use lexicographic range for RowKey prefix 'sc:'
        return list(
            self._client.query_entities(
                f"PartitionKey eq '{session_id}' and RowKey ge 'sc:' and RowKey lt 'sc;'"
            )
        )
