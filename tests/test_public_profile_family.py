"""Standalone route/query tests; no production database or application startup."""
import ast
import unittest
from enum import Enum
from pathlib import Path
from types import SimpleNamespace


class Mode(str, Enum):
    OSU = "osu"
    MANIA = "mania"

    def __int__(self):
        return 3 if self == Mode.MANIA else 0

    def __str__(self):
        return self.value


class Predicate:
    def __init__(self, test): self.test = test
    def __invert__(self): return Predicate(lambda row: not self.test(row))


class Field:
    def __init__(self, name): self.name = name
    def __eq__(self, value): return Predicate(lambda row: getattr(row, self.name) == value)
    def in_(self, values): return Predicate(lambda row: getattr(row, self.name) in values)
    def asc(self): return self


class User:
    id = Field("id")
    def __init__(self, id, restricted=False): self.id, self.restricted = id, restricted
    async def is_restricted(self, _db): return self.restricted
    @staticmethod
    def is_restricted_query(_field): return Predicate(lambda row: row.restricted)


class Profiles:
    master_user_id, ruleset_id, created_at = Field("master_user_id"), Field("ruleset_id"), Field("created_at")


class Statistics:
    user_id, mode = Field("user_id"), Field("mode")


class Query:
    def __init__(self, table): self.table, self.filters = table, []
    def where(self, *filters): self.filters.extend(filters); return self
    def order_by(self, *_args): return self


class Error(Exception):
    def __init__(self, status_code, detail): self.status_code, self.detail = status_code, detail


class Database:
    def __init__(self):
        self.users = [User(100), User(101), User(102), User(103, True)]
        self.rows = {
            User: self.users,
            Profiles: [SimpleNamespace(master_user_id=100, profile_user_id=id, ruleset_id=mode, name=name) for id, mode, name in [(101, 0, "DT practice"), (102, 3, "Keys practice"), (103, 0, "Restricted")]],
            Statistics: [SimpleNamespace(user_id=100, mode=Mode.OSU, pp=9000, rank=5)],
        }
    async def get(self, _table, id): return next((u for u in self.users if u.id == id), None)
    async def exec(self, query):
        return SimpleNamespace(all=lambda: [row for row in self.rows[query.table] if all(p.test(row) for p in query.filters)])


async def resolve_master_user_id(_db, _id): return 100


async def get_rank(_db, stat): return stat.rank


source = Path(__file__).resolve().parents[1] / "app/router/v2/torii_sub_profiles.py"
function = next(n for n in ast.parse(source.read_text(encoding="utf-8")).body if isinstance(n, ast.AsyncFunctionDef) and n.name == "get_public_profiles")
function.decorator_list = []
namespace = dict(Database=Database, GameMode=Mode, User=User, ToriiSubProfile=Profiles, UserStatistics=Statistics,
                 HTTPException=Error, resolve_master_user_id=resolve_master_user_id, get_rank=get_rank, select=Query, col=lambda value: value)
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
get_profiles = namespace["get_public_profiles"]


class PublicProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_main_and_persona_stats_are_not_combined(self):
        result = await get_profiles(101, Database(), Mode.OSU)
        self.assertEqual([(p["user_id"], p["pp"]) for p in result["profiles"]], [(100, 9000), (101, 0)])
        self.assertEqual(set(result), {"master_user_id", "mode", "profiles"})
        self.assertEqual(set(result["profiles"][1]), {"user_id", "name", "is_main", "pp", "global_rank"})

    async def test_modes_have_separate_profiles(self):
        result = await get_profiles(100, Database(), Mode.MANIA)
        self.assertEqual([p["name"] for p in result["profiles"]], ["Main", "Keys practice"])
        self.assertTrue(all(p["pp"] == 0 for p in result["profiles"]))

    async def test_restricted_and_unknown_users_are_not_exposed(self):
        for id in (103, 999):
            with self.subTest(id=id), self.assertRaises(Error) as error:
                await get_profiles(id, Database(), Mode.OSU)
            self.assertEqual(error.exception.status_code, 404)

    async def test_restricted_master_hides_family(self):
        db = Database()
        db.users[0].restricted = True
        with self.assertRaises(Error) as error:
            await get_profiles(101, db, Mode.OSU)
        self.assertEqual(error.exception.status_code, 404)


if __name__ == "__main__": unittest.main()
