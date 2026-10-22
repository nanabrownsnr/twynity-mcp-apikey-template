"""API-key encryption, upsert shape, and strict persona isolation tests.

Also asserts the Twynity §11.3 security note: the key value must NEVER appear
in list/read (public_metadata) responses — only the non-secret name does.
"""

import pytest
from cryptography.fernet import Fernet

from app.connection_store import ApiKeyStore


class FakeCollection:
    def __init__(self):
        self.documents = {}

    async def create_index(self, *_args, **_kwargs):
        return "user_persona_unique"

    async def update_one(self, query, update, upsert=False):
        key = (query["user_id"], query["persona_id"])
        document = self.documents.setdefault(key, {"_id": f"{key[0]}:{key[1]}"})
        document.update(update["$set"])
        return type("Result", (), {"upserted_id": None})()

    async def find_one(self, query, projection=None):
        document = self.documents.get((query["user_id"], query["persona_id"]))
        if not document:
            return None
        if projection:
            values = document.get("values", {})
            return {"_id": document["_id"], "values": {
                key: values[key] for key in ("name",) if key in values
            }}
        return document


@pytest.mark.asyncio
async def test_key_is_encrypted_and_only_retrieved_for_exact_pair():
    collection = FakeCollection()
    store = ApiKeyStore(collection, Fernet.generate_key().decode())
    await store.setup()
    await store.save("user-1", "persona-a", "GitHub PAT", "ghp_secretvalue123")

    stored = collection.documents[("user-1", "persona-a")]["values"]
    # The raw key must be Fernet-encrypted at rest, never stored in plaintext.
    assert "ghp_secretvalue123" not in stored["key"]
    # Strict persona isolation: a different persona sees nothing.
    assert await store.get("user-1", "persona-b") is None
    # The exact pair can read the decrypted key.
    assert (await store.get("user-1", "persona-a"))["key"] == "ghp_secretvalue123"


@pytest.mark.asyncio
async def test_public_metadata_never_exposes_the_key():
    collection = FakeCollection()
    store = ApiKeyStore(collection, Fernet.generate_key().decode())
    await store.setup()
    await store.save("user-1", "persona-a", "GitHub PAT", "ghp_secretvalue123")

    metadata = await store.public_metadata("user-1", "persona-a")
    assert metadata == {"id": "user-1:persona-a", "name": "GitHub PAT"}
    # §11.3 — the key must never leak into a list/read response.
    assert "key" not in metadata
    assert "ghp_secretvalue123" not in str(metadata)
