"""Replay extras: what a Torii client saves along with a replay.

A play made in VR records where the player's head and controllers were, so the
replay can show them again. The client keeps that in a file of its own next to
the replay (an "OSRX" file: tagged sections, so other kinds of extras can join
later) and uploads it here once the score is submitted. Whoever downloads the
replay fetches it from here as well.

The server only keeps the file. It doesn't read what's in it beyond the header,
and nothing here affects the score.
"""

from typing import Annotated

from app.database.score import Score
from app.dependencies.database import Database
from app.dependencies.storage import StorageService
from app.dependencies.user import ClientUser
from app.log import log

from .router import router

from fastapi import File, HTTPException, Response

logger = log("ReplayExtras")

# A five minute play in VR is about 150 KB; this is room for an hour of it.
MAX_EXTRAS_SIZE = 2 * 1024 * 1024

# Every extras file starts with this. What follows (the layout's version, then
# tagged sections) is the client's business: a newer client may store kinds of
# extras, or a layout, that this server has never heard of, and they are kept
# all the same.
_MAGIC = b"OSRX"


def _is_extras_file(content: bytes) -> bool:
    return len(content) > len(_MAGIC) and content.startswith(_MAGIC)


@router.put(
    "/score/{score_id}/extras",
    name="Upload replay extras",
    tags=["成绩", "g0v0 API"],
    status_code=204,
)
async def upload_replay_extras(
    session: Database,
    score_id: int,
    content: Annotated[bytes, File(...)],
    current_user: ClientUser,
    storage: StorageService,
):
    """Stores the extras file of one of the user's own scores, replacing any there is.

    Errors:
    - 400: not an extras file
    - 404: no such score of this user
    - 413: larger than 2 MB
    """
    if len(content) > MAX_EXTRAS_SIZE:
        raise HTTPException(status_code=413, detail="Replay extras are too large")

    if not _is_extras_file(content):
        raise HTTPException(status_code=400, detail="Not a replay extras file")

    score = await session.get(Score, score_id)
    if not score or score.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Score not found")

    # Read back through the API (below), never by its storage URL: not to be
    # cached anywhere as if it couldn't change.
    await storage.write_file(score.replay_extras_filename, content, "application/octet-stream", "private, no-store")
    logger.info(f"Stored {len(content)} bytes of replay extras for score {score_id}")


@router.get(
    "/score/{score_id}/extras",
    name="Download replay extras",
    tags=["成绩", "g0v0 API"],
    responses={200: {"content": {"application/octet-stream": {}}}},
)
async def download_replay_extras(
    session: Database,
    score_id: int,
    current_user: ClientUser,
    storage: StorageService,
):
    """The extras file of a score, as it was uploaded.

    Errors:
    - 404: no such score, or it has no extras
    """
    score = await session.get(Score, score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")

    path = score.replay_extras_filename

    if not await storage.is_exists(path):
        raise HTTPException(status_code=404, detail="Score has no replay extras")

    return Response(content=await storage.read_file(path), media_type="application/octet-stream")
