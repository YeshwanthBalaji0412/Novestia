"""Cursor-based pagination utility.

Encodes/decodes opaque cursors for stable pagination across inserts.
Cursor format: base64(json({"ts": iso_timestamp, "id": uuid_string}))
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Cursor:
    """A decoded pagination cursor."""

    timestamp: datetime
    id: uuid.UUID


def encode_cursor(timestamp: datetime, row_id: uuid.UUID) -> str:
    """Encode a timestamp + id into an opaque cursor string."""
    payload = json.dumps({"ts": timestamp.isoformat(), "id": str(row_id)})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> Cursor:
    """Decode an opaque cursor string back to timestamp + id."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return Cursor(
            timestamp=datetime.fromisoformat(payload["ts"]),
            id=uuid.UUID(payload["id"]),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        msg = "Invalid pagination cursor"
        raise ValueError(msg) from e
