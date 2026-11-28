from functools import partial

from app.database.score import Beatmap, Score
from app.models.achievement import Achievement, Medals
from app.models.mods import API_MODS

from sqlmodel.ext.asyncio.session import AsyncSession


async def process_mod(
    mod: str,
    session: AsyncSession,
    score: Score,
    beatmap: Beatmap,
) -> bool:
    if not score.passed:
        return False
    if not beatmap.beatmap_status.has_leaderboard():
        return False
    return not (len(score.mods) != 1 or score.mods[0]["acronym"] != mod)


async def process_category_mod(
    category: str,
    session: AsyncSession,
    score: Score,
    beatmap: Beatmap,
) -> bool:
    if not score.passed:
        return False
    if not beatmap.beatmap_status.has_leaderboard():
        return False
    if len(score.mods) == 0:
        return False
    api_mods = {
        k
        for k, v in API_MODS[int(score.gamemode)].items()  # pyright: ignore[reportArgumentType]
        if v["Type"] == category
    }
    return all(mod["acronym"] in api_mods for mod in score.mods)


MEDALS: Medals = {
    Achievement(
        id=89,
        name='Last Breath',
        desc='One slip and the run is over.',
        assets_id='all-intro-suddendeath',
    ): partial(process_mod, "SD"),
    Achievement(
        id=90,
        name='Crowned Precision',
        desc='Nothing short of perfection.',
        assets_id='all-intro-perfect',
    ): partial(process_mod, "PF"),
    Achievement(
        id=91,
        name='Cracked Crystal',
        desc='Sharper edges, tighter windows.',
        assets_id='all-intro-hardrock',
    ): partial(process_mod, "HR"),
    Achievement(
        id=92,
        name='Twin Velocity',
        desc='Push the tempo past its normal limits.',
        assets_id='all-intro-doubletime',
    ): partial(process_mod, "DT"),
    Achievement(
        id=93,
        name='Winged Tempo',
        desc='Higher pitch, faster pulse.',
        assets_id='all-intro-nightcore',
    ): partial(process_mod, "NC"),
    Achievement(
        id=94,
        name='Blind Strike',
        desc='Trust your instincts when the circles fade.',
        assets_id='all-intro-hidden',
    ): partial(process_mod, "HD"),
    Achievement(
        id=95,
        name='Lantern Beam',
        desc='A narrow cone of light in the dark.',
        assets_id='all-intro-flashlight',
    ): partial(process_mod, "FL"),
    Achievement(
        id=96,
        name='Feather Touch',
        desc='A gentler pace to find your footing.',
        assets_id='all-intro-easy',
    ): partial(process_mod, "EZ"),
    Achievement(
        id=97,
        name='Heart Shield',
        desc='Keep playing even when the pressure mounts.',
        assets_id='all-intro-nofail',
    ): partial(process_mod, "NF"),
    Achievement(
        id=98,
        name='Snail Drift',
        desc='Slow the world down and read every note.',
        assets_id='all-intro-halftime',
    ): partial(process_mod, "HT"),
    Achievement(
        id=99,
        name='Idle Spiral',
        desc='Let the spinners turn on their own.',
        assets_id='all-intro-spunout',
    ): partial(process_mod, "SO"),
    Achievement(
        id=100,
        name='Gear Swap',
        desc='Reforge the map to your favorite discipline.',
        assets_id='all-intro-conversion',
    ): partial(process_category_mod, "Conversion"),
    Achievement(
        id=101,
        name='Arcade Spark',
        desc='Just here for the pure fun of it.',
        assets_id='all-intro-fun',
    ): partial(process_category_mod, "Fun"),
}
