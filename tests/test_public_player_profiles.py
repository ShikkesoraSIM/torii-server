"""Read-only profile family projection, including the legacy production schema."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

from test_public_profile_family import Database, Error, Field, Mode, Profiles, Query, Statistics, User

Profiles.profile_user_id = Field("profile_user_id")


class FamilyDatabase(Database):
    async def exec(self, query):
        if query.table is User.id:
            source, projection = self.users, lambda row: row.id
        elif query.table is Profiles.master_user_id:
            source, projection = self.rows[Profiles], lambda row: row.master_user_id
        else:
            source, projection = self.rows[query.table], lambda row: row
        rows = [projection(row) for row in source if all(p.test(row) for p in query.filters)]
        return SimpleNamespace(all=lambda: rows, first=lambda: rows[0] if rows else None)


async def rank(_db, stat):
    return stat.rank


source = Path(__file__).resolve().parents[1] / "app/router/private/player_profiles.py"
function = next(node for node in ast.parse(source.read_text(encoding="utf-8")).body
                if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_public_profiles")
function.decorator_list = []
namespace = dict(Database=FamilyDatabase, GameMode=Mode, User=User, ToriiSubProfile=Profiles,
                 UserStatistics=Statistics, HTTPException=Error, select=Query,
                 col=lambda value: value, get_rank=rank)
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
get_profiles = namespace["get_public_profiles"]


class PublicPlayerProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_persona_has_own_stats_and_no_secrets(self):
        result = await get_profiles(101, FamilyDatabase(), Mode.OSU)
        self.assertEqual([(p["user_id"], p["pp"]) for p in result["profiles"]], [(100, 9000), (101, 0)])
        self.assertEqual(result["profiles"][0]["global_rank"], 5)
        self.assertEqual(set(result["profiles"][1]), {"user_id", "name", "is_main", "pp", "global_rank"})

    async def test_separate_rulesets(self):
        result = await get_profiles(100, FamilyDatabase(), Mode.MANIA)
        self.assertEqual([p["name"] for p in result["profiles"]], ["Main", "Keys practice"])

    async def test_legacy_profiles_only_in_standard(self):
        db = FamilyDatabase()
        del db.rows[Profiles][0].ruleset_id
        self.assertIn(101, [p["user_id"] for p in (await get_profiles(100, db, Mode.OSU))["profiles"]])
        self.assertNotIn(101, [p["user_id"] for p in (await get_profiles(100, db, Mode.MANIA))["profiles"]])

    async def test_unknown_and_restricted_users(self):
        for user_id in (103, 999):
            with self.assertRaises(Error) as error:
                await get_profiles(user_id, FamilyDatabase(), Mode.OSU)
            self.assertEqual(error.exception.status_code, 404)

    async def test_restricted_master_hides_family(self):
        db = FamilyDatabase()
        db.users[0].restricted = True
        with self.assertRaises(Error):
            await get_profiles(101, db, Mode.OSU)

    async def test_no_family_still_returns_main(self):
        db = FamilyDatabase()
        db.rows[Profiles] = []
        result = await get_profiles(100, db, Mode.OSU)
        self.assertEqual([p["name"] for p in result["profiles"]], ["Main"])


if __name__ == "__main__":
    unittest.main()
