from functools import partial

from app.database.score import Beatmap, Score
from app.models.achievement import Achievement, Medals
from app.models.score import GameMode

from sqlmodel.ext.asyncio.session import AsyncSession


async def process_combo(
    combo: int,
    next_combo: int,
    session: AsyncSession,
    score: Score,
    beatmap: Beatmap,
) -> bool:
    if not score.passed or not beatmap.beatmap_status.has_pp() or score.gamemode != GameMode.OSU:
        return False
    if combo < 1:
        return False
    if next_combo != 0 and combo >= next_combo:
        return False
    return bool(combo <= score.max_combo < next_combo or (next_combo == 0 and score.max_combo >= combo))


MEDALS: Medals = {
    Achievement(
        id=21,
        name='500x Spark',
        desc='500 hits linked without breaking stride.',
        assets_id='osu-combo-500',
    ): partial(process_combo, 500, 750),
    Achievement(
        id=22,
        name='750x Surge',
        desc='750 notes chained in clean rhythm.',
        assets_id='osu-combo-750',
    ): partial(process_combo, 750, 1000),
    Achievement(
        id=23,
        name='1000x Storm',
        desc='A thousand consecutive hits.',
        assets_id='osu-combo-1000',
    ): partial(process_combo, 1000, 2000),
    Achievement(
        id=24,
        name='2000x Thunder',
        desc='Two thousand hits without a single miss.',
        assets_id='osu-combo-2000',
    ): partial(process_combo, 2000, 0),
}
