"""Derive a user's client STREAM (torii / nova / vanilla / other) from their
last resolved client hash.

Pipeline:  Redis 'metadata:user:last_client_hash:{id}'  ->
           ClientVerificationService.versions[hash] -> client_name -> stream token.

The stream is a coarse brand bucket used by the online dashboard's "which client
is this user on" glyph. It is intentionally a pure function of the target user
(no viewer context) so it can be cached; the viewer-on-vanilla HIDE rule lives in
the frontend (it hides the glyph when the VIEWER's own stream is 'vanilla').
"""

from __future__ import annotations

from typing import Literal

from app.service.client_verification_service import ClientVerificationService

ClientStream = Literal["torii", "nova", "vanilla", "other"]

LAST_CLIENT_HASH_KEY = "metadata:user:last_client_hash:{user_id}"


def classify_client_stream(client_name: str | None) -> ClientStream:
    """Map a registered client display name to a coarse stream token.

    Order matters: 'Torii Vanilla' and 'Torii Nova' both contain 'torii', so the
    specific streams must be checked before the bare-torii fallback.
    """
    canonical = (client_name or "").strip().lower().replace("!", "").replace(" ", "")
    if not canonical:
        return "other"
    if "vanilla" in canonical and "torii" in canonical:
        return "vanilla"
    if "nova" in canonical and "torii" in canonical:
        return "nova"
    if "torii" in canonical:
        return "torii"
    return "other"


async def resolve_client_stream(
    redis,
    verification_service: ClientVerificationService,
    user_id: int,
) -> ClientStream:
    """Resolve one user's current stream from their last stored client hash."""
    raw = await redis.get(LAST_CLIENT_HASH_KEY.format(user_id=user_id))
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    client_hash = (raw or "").strip().lower()
    if not client_hash:
        return "other"

    entry = verification_service.versions.get(client_hash)
    if not entry:
        return "other"

    client_name = entry[0]  # (client_name, version, os)
    return classify_client_stream(client_name)
