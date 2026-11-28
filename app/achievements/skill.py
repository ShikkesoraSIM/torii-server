from functools import partial
from typing import Literal, cast

from app.database.beatmap import calculate_beatmap_attributes
from app.database.score import Beatmap, Score
from app.dependencies.database import get_redis
from app.dependencies.fetcher import get_fetcher
from app.models.achievement import Achievement, Medals
from app.models.mods import API_MODS, mods_can_get_pp_vanilla
from app.models.score import GameMode

from sqlmodel.ext.asyncio.session import AsyncSession


async def process_skill(
    target_gamemode: GameMode,
    star: int,
    type: Literal["pass", "fc"],
    session: AsyncSession,
    score: Score,
    beatmap: Beatmap,
) -> bool:
    if target_gamemode != score.gamemode:
        return False
    ruleset_id = int(score.gamemode)
    if not score.passed:
        return False
    if not beatmap.beatmap_status.has_pp():
        return False
    if not mods_can_get_pp_vanilla(ruleset_id, score.mods):
        return False
    difficulty_reduction_mods = [
        mod["Acronym"]
        for mod in API_MODS[cast(Literal[0, 1, 2, 3], ruleset_id)].values()
        if mod["Type"] == "DifficultyReduction"
    ]
    for mod in score.mods:
        if mod["acronym"] in difficulty_reduction_mods:
            return False

    fetcher = await get_fetcher()
    redis = get_redis()
    mods_ = score.mods.copy()
    mods_.sort(key=lambda x: x["acronym"])
    attribute = await calculate_beatmap_attributes(beatmap.id, score.gamemode, mods_, redis, fetcher)
    if attribute.star_rating < star or attribute.star_rating >= star + 1:
        return False
    return not (type == "fc" and not score.is_perfect_combo)


MEDALS: Medals = {
    Achievement(
        id=1,
        name='First Spark',
        desc='Your first step under the Torii gate.',
        assets_id='osu-skill-pass-1',
    ): partial(process_skill, GameMode.OSU, 1, "pass"),
    Achievement(
        id=2,
        name='Twin Orbits',
        desc='Two stars circling into rhythm.',
        assets_id='osu-skill-pass-2',
    ): partial(process_skill, GameMode.OSU, 2, "pass"),
    Achievement(
        id=3,
        name='Crescent Rise',
        desc='Finding calm precision under the moon.',
        assets_id='osu-skill-pass-3',
    ): partial(process_skill, GameMode.OSU, 3, "pass"),
    Achievement(
        id=4,
        name='Comet Trail',
        desc='Cutting cleanly through faster patterns.',
        assets_id='osu-skill-pass-4',
    ): partial(process_skill, GameMode.OSU, 4, "pass"),
    Achievement(
        id=5,
        name='Radiant Star',
        desc='Shining steady through five-star storms.',
        assets_id='osu-skill-pass-5',
    ): partial(process_skill, GameMode.OSU, 5, "pass"),
    Achievement(
        id=6,
        name='Winged Crest',
        desc='Soaring past the six-star threshold.',
        assets_id='osu-skill-pass-6',
    ): partial(process_skill, GameMode.OSU, 6, "pass"),
    Achievement(
        id=7,
        name='Crossed Katanas',
        desc='Sharp aim and blades in sync.',
        assets_id='osu-skill-pass-7',
    ): partial(process_skill, GameMode.OSU, 7, "pass"),
    Achievement(
        id=8,
        name='Beacon Halo',
        desc='Eight stars of focused clarity.',
        assets_id='osu-skill-pass-8',
    ): partial(process_skill, GameMode.OSU, 8, "pass"),
    Achievement(
        id=9,
        name='Rising Phoenix',
        desc='Reborn through nine-star intensity.',
        assets_id='osu-skill-pass-9',
    ): partial(process_skill, GameMode.OSU, 9, "pass"),
    Achievement(
        id=10,
        name='Torii Zenith',
        desc='Standing at the ten-star summit.',
        assets_id='osu-skill-pass-10',
    ): partial(process_skill, GameMode.OSU, 10, "pass"),
    Achievement(
        id=11,
        name='Diamond Spark',
        desc='A spotless first full combo.',
        assets_id='osu-skill-fc-1',
    ): partial(process_skill, GameMode.OSU, 1, "fc"),
    Achievement(
        id=12,
        name='Twin Rings',
        desc='Two unbroken circles locked together.',
        assets_id='osu-skill-fc-2',
    ): partial(process_skill, GameMode.OSU, 2, "fc"),
    Achievement(
        id=13,
        name='Laurel Arc',
        desc='Crowned in three-star consistency.',
        assets_id='osu-skill-fc-3',
    ): partial(process_skill, GameMode.OSU, 3, "fc"),
    Achievement(
        id=14,
        name='Starblade',
        desc='Four stars sliced without a break.',
        assets_id='osu-skill-fc-4',
    ): partial(process_skill, GameMode.OSU, 4, "fc"),
    Achievement(
        id=15,
        name='Faceted Jewel',
        desc='Five stars held with crystal precision.',
        assets_id='osu-skill-fc-5',
    ): partial(process_skill, GameMode.OSU, 5, "fc"),
    Achievement(
        id=16,
        name='Blade Wings',
        desc='Six-star full combo in full flight.',
        assets_id='osu-skill-fc-6',
    ): partial(process_skill, GameMode.OSU, 6, "fc"),
    Achievement(
        id=17,
        name='Royal Crown',
        desc='Seven stars conquered without a miss.',
        assets_id='osu-skill-fc-7',
    ): partial(process_skill, GameMode.OSU, 7, "fc"),
    Achievement(
        id=18,
        name='Compass Halo',
        desc='Eight-star mastery in every direction.',
        assets_id='osu-skill-fc-8',
    ): partial(process_skill, GameMode.OSU, 8, "fc"),
    Achievement(
        id=19,
        name='Dragon Crest',
        desc='Nine stars tamed from start to finish.',
        assets_id='osu-skill-fc-9',
    ): partial(process_skill, GameMode.OSU, 9, "fc"),
    Achievement(
        id=20,
        name='Winged Torii',
        desc='Ten-star perfection under the shrine.',
        assets_id='osu-skill-fc-10',
    ): partial(process_skill, GameMode.OSU, 10, "fc"),
    Achievement(
        id=25,
        name='First Spark (Drums)',
        desc='Your first step under the Torii gate.',
        assets_id='taiko-skill-pass-1',
    ): partial(process_skill, GameMode.TAIKO, 1, "pass"),
    Achievement(
        id=26,
        name='Twin Orbits (Drums)',
        desc='Two stars circling into rhythm.',
        assets_id='taiko-skill-pass-2',
    ): partial(process_skill, GameMode.TAIKO, 2, "pass"),
    Achievement(
        id=27,
        name='Crescent Rise (Drums)',
        desc='Finding calm precision under the moon.',
        assets_id='taiko-skill-pass-3',
    ): partial(process_skill, GameMode.TAIKO, 3, "pass"),
    Achievement(
        id=28,
        name='Comet Trail (Drums)',
        desc='Cutting cleanly through faster patterns.',
        assets_id='taiko-skill-pass-4',
    ): partial(process_skill, GameMode.TAIKO, 4, "pass"),
    Achievement(
        id=29,
        name='Radiant Star (Drums)',
        desc='Shining steady through five-star storms.',
        assets_id='taiko-skill-pass-5',
    ): partial(process_skill, GameMode.TAIKO, 5, "pass"),
    Achievement(
        id=30,
        name='Winged Crest (Drums)',
        desc='Soaring past the six-star threshold.',
        assets_id='taiko-skill-pass-6',
    ): partial(process_skill, GameMode.TAIKO, 6, "pass"),
    Achievement(
        id=31,
        name='Crossed Katanas (Drums)',
        desc='Sharp aim and blades in sync.',
        assets_id='taiko-skill-pass-7',
    ): partial(process_skill, GameMode.TAIKO, 7, "pass"),
    Achievement(
        id=32,
        name='Beacon Halo (Drums)',
        desc='Eight stars of focused clarity.',
        assets_id='taiko-skill-pass-8',
    ): partial(process_skill, GameMode.TAIKO, 8, "pass"),
    Achievement(
        id=33,
        name='Diamond Spark (Drums)',
        desc='A spotless first full combo.',
        assets_id='taiko-skill-fc-1',
    ): partial(process_skill, GameMode.TAIKO, 1, "fc"),
    Achievement(
        id=34,
        name='Twin Rings (Drums)',
        desc='Two unbroken circles locked together.',
        assets_id='taiko-skill-fc-2',
    ): partial(process_skill, GameMode.TAIKO, 2, "fc"),
    Achievement(
        id=35,
        name='Laurel Arc (Drums)',
        desc='Crowned in three-star consistency.',
        assets_id='taiko-skill-fc-3',
    ): partial(process_skill, GameMode.TAIKO, 3, "fc"),
    Achievement(
        id=36,
        name='Starblade (Drums)',
        desc='Four stars sliced without a break.',
        assets_id='taiko-skill-fc-4',
    ): partial(process_skill, GameMode.TAIKO, 4, "fc"),
    Achievement(
        id=37,
        name='Faceted Jewel (Drums)',
        desc='Five stars held with crystal precision.',
        assets_id='taiko-skill-fc-5',
    ): partial(process_skill, GameMode.TAIKO, 5, "fc"),
    Achievement(
        id=38,
        name="Blade Wings (Drums)",
        desc="Six-star full combo in full flight.",
        assets_id="taiko-skill-fc-6",
    ): partial(process_skill, GameMode.TAIKO, 6, "fc"),
    Achievement(
        id=39,
        name='Royal Crown (Drums)',
        desc='Seven stars conquered without a miss.',
        assets_id='taiko-skill-fc-7',
    ): partial(process_skill, GameMode.TAIKO, 7, "fc"),
    Achievement(
        id=40,
        name="Compass Halo (Drums)",
        desc="Eight-star mastery in every direction.",
        assets_id="taiko-skill-fc-8",
    ): partial(process_skill, GameMode.TAIKO, 8, "fc"),
    Achievement(
        id=41,
        name='First Spark (Catch)',
        desc='Your first step under the Torii gate.',
        assets_id='fruits-skill-pass-1',
    ): partial(process_skill, GameMode.FRUITS, 1, "pass"),
    Achievement(
        id=42,
        name='Twin Orbits (Catch)',
        desc='Two stars circling into rhythm.',
        assets_id='fruits-skill-pass-2',
    ): partial(process_skill, GameMode.FRUITS, 2, "pass"),
    Achievement(
        id=43,
        name='Crescent Rise (Catch)',
        desc='Finding calm precision under the moon.',
        assets_id='fruits-skill-pass-3',
    ): partial(process_skill, GameMode.FRUITS, 3, "pass"),
    Achievement(
        id=44,
        name='Comet Trail (Catch)',
        desc='Cutting cleanly through faster patterns.',
        assets_id='fruits-skill-pass-4',
    ): partial(process_skill, GameMode.FRUITS, 4, "pass"),
    Achievement(
        id=45,
        name="Radiant Star (Catch)",
        desc="Shining steady through five-star storms.",
        assets_id="fruits-skill-pass-5",
    ): partial(process_skill, GameMode.FRUITS, 5, "pass"),
    Achievement(
        id=46,
        name='Winged Crest (Catch)',
        desc='Soaring past the six-star threshold.',
        assets_id='fruits-skill-pass-6',
    ): partial(process_skill, GameMode.FRUITS, 6, "pass"),
    Achievement(
        id=47,
        name='Crossed Katanas (Catch)',
        desc='Sharp aim and blades in sync.',
        assets_id='fruits-skill-pass-7',
    ): partial(process_skill, GameMode.FRUITS, 7, "pass"),
    Achievement(
        id=48,
        name='Beacon Halo (Catch)',
        desc='Eight stars of focused clarity.',
        assets_id='fruits-skill-pass-8',
    ): partial(process_skill, GameMode.FRUITS, 8, "pass"),
    Achievement(
        id=49,
        name='Diamond Spark (Catch)',
        desc='A spotless first full combo.',
        assets_id='fruits-skill-fc-1',
    ): partial(process_skill, GameMode.FRUITS, 1, "fc"),
    Achievement(
        id=50,
        name='Twin Rings (Catch)',
        desc='Two unbroken circles locked together.',
        assets_id='fruits-skill-fc-2',
    ): partial(process_skill, GameMode.FRUITS, 2, "fc"),
    Achievement(
        id=51,
        name='Laurel Arc (Catch)',
        desc='Crowned in three-star consistency.',
        assets_id='fruits-skill-fc-3',
    ): partial(process_skill, GameMode.FRUITS, 3, "fc"),
    Achievement(
        id=52,
        name='Starblade (Catch)',
        desc='Four stars sliced without a break.',
        assets_id='fruits-skill-fc-4',
    ): partial(process_skill, GameMode.FRUITS, 4, "fc"),
    Achievement(
        id=53,
        name='Faceted Jewel (Catch)',
        desc='Five stars held with crystal precision.',
        assets_id='fruits-skill-fc-5',
    ): partial(process_skill, GameMode.FRUITS, 5, "fc"),
    Achievement(
        id=54,
        name='Blade Wings (Catch)',
        desc='Six-star full combo in full flight.',
        assets_id='fruits-skill-fc-6',
    ): partial(process_skill, GameMode.FRUITS, 6, "fc"),
    Achievement(
        id=55,
        name='Royal Crown (Catch)',
        desc='Seven stars conquered without a miss.',
        assets_id='fruits-skill-fc-7',
    ): partial(process_skill, GameMode.FRUITS, 7, "fc"),
    Achievement(
        id=56,
        name='Compass Halo (Catch)',
        desc='Eight-star mastery in every direction.',
        assets_id='fruits-skill-fc-8',
    ): partial(process_skill, GameMode.FRUITS, 8, "fc"),
    Achievement(
        id=57,
        name='First Spark (Keys)',
        desc='Your first step under the Torii gate.',
        assets_id='mania-skill-pass-1',
    ): partial(process_skill, GameMode.MANIA, 1, "pass"),
    Achievement(
        id=58,
        name='Twin Orbits (Keys)',
        desc='Two stars circling into rhythm.',
        assets_id='mania-skill-pass-2',
    ): partial(process_skill, GameMode.MANIA, 2, "pass"),
    Achievement(
        id=59,
        name='Crescent Rise (Keys)',
        desc='Finding calm precision under the moon.',
        assets_id='mania-skill-pass-3',
    ): partial(process_skill, GameMode.MANIA, 3, "pass"),
    Achievement(
        id=60,
        name='Comet Trail (Keys)',
        desc='Cutting cleanly through faster patterns.',
        assets_id='mania-skill-pass-4',
    ): partial(process_skill, GameMode.MANIA, 4, "pass"),
    Achievement(
        id=61,
        name='Radiant Star (Keys)',
        desc='Shining steady through five-star storms.',
        assets_id='mania-skill-pass-5',
    ): partial(process_skill, GameMode.MANIA, 5, "pass"),
    Achievement(
        id=62,
        name='Winged Crest (Keys)',
        desc='Soaring past the six-star threshold.',
        assets_id='mania-skill-pass-6',
    ): partial(process_skill, GameMode.MANIA, 6, "pass"),
    Achievement(
        id=63,
        name='Crossed Katanas (Keys)',
        desc='Sharp aim and blades in sync.',
        assets_id='mania-skill-pass-7',
    ): partial(process_skill, GameMode.MANIA, 7, "pass"),
    Achievement(
        id=64,
        name='Beacon Halo (Keys)',
        desc='Eight stars of focused clarity.',
        assets_id='mania-skill-pass-8',
    ): partial(process_skill, GameMode.MANIA, 8, "pass"),
    Achievement(
        id=65,
        name='Diamond Spark (Keys)',
        desc='A spotless first full combo.',
        assets_id='mania-skill-fc-1',
    ): partial(process_skill, GameMode.MANIA, 1, "fc"),
    Achievement(
        id=66,
        name='Twin Rings (Keys)',
        desc='Two unbroken circles locked together.',
        assets_id='mania-skill-fc-2',
    ): partial(process_skill, GameMode.MANIA, 2, "fc"),
    Achievement(
        id=67,
        name='Laurel Arc (Keys)',
        desc='Crowned in three-star consistency.',
        assets_id='mania-skill-fc-3',
    ): partial(process_skill, GameMode.MANIA, 3, "fc"),
    Achievement(
        id=68,
        name='Starblade (Keys)',
        desc='Four stars sliced without a break.',
        assets_id='mania-skill-fc-4',
    ): partial(process_skill, GameMode.MANIA, 4, "fc"),
    Achievement(
        id=69,
        name='Faceted Jewel (Keys)',
        desc='Five stars held with crystal precision.',
        assets_id='mania-skill-fc-5',
    ): partial(process_skill, GameMode.MANIA, 5, "fc"),
    Achievement(
        id=70,
        name='Blade Wings (Keys)',
        desc='Six-star full combo in full flight.',
        assets_id='mania-skill-fc-6',
    ): partial(process_skill, GameMode.MANIA, 6, "fc"),
    Achievement(
        id=71,
        name='Royal Crown (Keys)',
        desc='Seven stars conquered without a miss.',
        assets_id='mania-skill-fc-7',
    ): partial(process_skill, GameMode.MANIA, 7, "fc"),
    Achievement(
        id=72,
        name='Compass Halo (Keys)',
        desc='Eight-star mastery in every direction.',
        assets_id='mania-skill-fc-8',
    ): partial(process_skill, GameMode.MANIA, 8, "fc"),
}
