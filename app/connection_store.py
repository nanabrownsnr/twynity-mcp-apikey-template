"""Encrypted MongoDB persistence for a user's stored API key.

A single API key is stored per exact ``(user_id, persona_id)`` pair. The key
value is Fernet-encrypted at rest and is only decrypted when a tool reads it
back for an actual API call. List/read responses expose only the non-secret
``name`` field — never the key (Twynity compliance section 11.3 security note).
"""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from cryptography.fernet import Fernet, InvalidToken
from pymongo import ASCENDING

_active_store: "ApiKeyStore | None" = None


def set_active_store(store: "ApiKeyStore | None") -> None:
    """Set the process-scoped store created/closed by the ASGI lifespan."""
    global _active_store
    _active_store = store


def get_active_store() -> "ApiKeyStore | None":
    return _active_store


class ApiKeyStore:
    """Store one upserted API key per exact ``(user_id, persona_id)`` pair."""

    def __init__(self, collection: Any, encryption_key: str):
        self.collection = collection
        self.cipher = Fernet(encryption_key.encode("ascii"))

    async def setup(self) -> None:
        """Create the compound uniqueness constraint at application startup."""
        await self.collection.create_index(
            [("user_id", ASCENDING), ("persona_id", ASCENDING)], unique=True
        )

    async def save(self, user_id: str, persona_id: str, name: str, key: str) -> str:
        """Encrypt the key and upsert only this user/persona's stored key."""
        now = datetime.now(UTC)
        encrypted = {
            "name": self.cipher.encrypt(name.encode("utf-8")).decode("ascii"),
            "key": self.cipher.encrypt(key.encode("utf-8")).decode("ascii"),
        }
        result = await self.collection.update_one(
            {"user_id": user_id, "persona_id": persona_id},
            {
                "$set": {"values": encrypted, "modified": now},
                "$setOnInsert": {"created": now},
            },
            upsert=True,
        )
        return str(result.upserted_id) if result.upserted_id else "updated"

    async def get(self, user_id: str, persona_id: str) -> dict[str, Any] | None:
        """Read and decrypt the exact identity pair; never search by user alone."""
        document = await self.collection.find_one(
            {"user_id": user_id, "persona_id": persona_id}
        )
        if not document:
            return None
        try:
            values = {
                key: self.cipher.decrypt(value.encode("ascii")).decode("utf-8")
                for key, value in document["values"].items()
            }
        except (InvalidToken, KeyError, TypeError) as exc:
            raise RuntimeError("Stored API key could not be decrypted; check ENCRYPTION_KEY") from exc
        return {"id": str(document.get("_id", ObjectId())), **values}

    async def public_metadata(self, user_id: str, persona_id: str) -> dict[str, Any] | None:
        """Return only the non-secret ``name`` field — never the key value."""
        document = await self.collection.find_one(
            {"user_id": user_id, "persona_id": persona_id},
            {"values.name": 1, "created": 1, "modified": 1},
        )
        if not document:
            return None
        values = document.get("values", {})
        safe: dict[str, Any] = {"id": str(document["_id"])}
        encrypted_name = values.get("name")
        if encrypted_name:
            safe["name"] = self.cipher.decrypt(encrypted_name.encode("ascii")).decode("utf-8")
        return safe
