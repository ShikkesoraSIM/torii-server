from . import beatmap  # noqa: F401
from .beatmapset import BeatmapsetModel, completar_covers

from pydantic import field_validator
from sqlmodel import SQLModel

# tags va aca porque el cliente y la web lo miran para el badge de mapas hechos
# con IA; sin declararlo, la respuesta lo descarta aunque lo llenemos.
SearchBeatmapset = BeatmapsetModel.generate_typeddict(
    ("beatmaps.max_combo", "pack_tags", "tags", "ai", "is_blacklisted", "has_blacklisted_difficulties", "beatmaps.is_blacklisted")
)


class SearchBeatmapsetsResp(SQLModel):
    beatmapsets: list[SearchBeatmapset]  # pyright: ignore[reportInvalidTypeForm]
    total: int
    cursor: dict[str, int | float | str] | None = None
    cursor_string: str | None = None

    @field_validator("beatmapsets", mode="before")
    @classmethod
    def _rewrite_search_covers(cls, v):
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and item.get("covers"):
                    item["covers"] = completar_covers(item["covers"])
        return v
