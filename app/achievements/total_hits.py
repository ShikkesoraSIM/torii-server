from functools import partial

from app.database.score import Beatmap, Score
from app.database.statistics import UserStatistics
from app.models.achievement import Achievement, Medals
from app.models.score import GameMode

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


async def process_tth(
    tth: int,
    next_tth: int,
    gamemode: GameMode,
    session: AsyncSession,
    score: Score,
    beatmap: Beatmap,
) -> bool:
    if tth < 1:
        return False
    if next_tth != 0 and tth >= next_tth:
        return False
    if score.gamemode != gamemode:
        return False
    stats = (
        await session.exec(
            select(UserStatistics).where(
                UserStatistics.mode == score.gamemode,
                UserStatistics.user_id == score.user_id,
            )
        )
    ).first()
    if not stats:
        return False
    return bool(tth <= stats.total_hits < next_tth or (next_tth == 0 and stats.play_count >= tth))


MEDALS: Medals = {
    Achievement(
        id=77,
        name='30,000 Drum Strikes',
        desc='Thirty thousand taiko beats landed.',
        assets_id='taiko-hits-30000',
    ): partial(process_tth, 30000, 300000, GameMode.TAIKO),
    Achievement(
        id=78,
        name='300,000 Drum Strikes',
        desc='Three hundred thousand drum hits.',
        assets_id='taiko-hits-300000',
    ): partial(process_tth, 300000, 3000000, GameMode.TAIKO),
    Achievement(
        id=79,
        name='3,000,000 Drum Strikes',
        desc='Three million resonant drum strikes.',
        assets_id='taiko-hits-3000000',
    ): partial(process_tth, 3000000, 30000000, GameMode.TAIKO),
    Achievement(
        id=80,
        name='30,000,000 Drum Strikes',
        desc='Thirty million drum strikes.',
        assets_id='taiko-hits-30000000',
    ): partial(process_tth, 30000000, 0, GameMode.TAIKO),
    Achievement(
        id=81,
        name='20,000 Catches',
        desc='Twenty thousand fruits caught.',
        assets_id='fruits-hits-20000',
    ): partial(process_tth, 20000, 200000, GameMode.FRUITS),
    Achievement(
        id=82,
        name='200,000 Catches',
        desc='Two hundred thousand fruits caught.',
        assets_id='fruits-hits-200000',
    ): partial(process_tth, 200000, 2000000, GameMode.FRUITS),
    Achievement(
        id=83,
        name='2,000,000 Catches',
        desc='Two million fruits caught.',
        assets_id='fruits-hits-2000000',
    ): partial(process_tth, 2000000, 20000000, GameMode.FRUITS),
    Achievement(
        id=84,
        name='20,000,000 Catches',
        desc='Twenty million fruits caught.',
        assets_id='fruits-hits-20000000',
    ): partial(process_tth, 20000000, 0, GameMode.FRUITS),
    Achievement(
        id=85,
        name='40,000 Keystrokes',
        desc='Forty thousand keys struck.',
        assets_id='mania-hits-40000',
    ): partial(process_tth, 40000, 400000, GameMode.MANIA),
    Achievement(
        id=86,
        name='400,000 Keystrokes',
        desc='Four hundred thousand keys struck.',
        assets_id='mania-hits-400000',
    ): partial(process_tth, 400000, 4000000, GameMode.MANIA),
    Achievement(
        id=87,
        name='4,000,000 Keystrokes',
        desc='Four million keys struck.',
        assets_id='mania-hits-4000000',
    ): partial(process_tth, 4000000, 40000000, GameMode.MANIA),
    Achievement(
        id=88,
        name='40,000,000 Keystrokes',
        desc='Forty million keys struck.',
        assets_id='mania-hits-40000000',
    ): partial(process_tth, 40000000, 0, GameMode.MANIA),
}
