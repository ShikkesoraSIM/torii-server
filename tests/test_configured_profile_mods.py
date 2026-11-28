import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("profile_policy", ROOT / "app/models/sub_profile_mod_policy.py")
policy_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy_module)
CATALOGS = {r["RulesetID"]: {m["Acronym"]: m for m in r["Mods"]} for r in json.loads((ROOT / "static/mods.json").read_text(encoding="utf-8"))}


class ConfiguredProfileTests(unittest.TestCase):
    def policy(self, **changes):
        result = dict(version=1, ruleset_id=0, required=[dict(acronym="DA", settings=dict(circle_size=9))], optional=["HD"], allow_other_mods=False)
        result.update(changes)
        return policy_module.validate_policy(result, CATALOGS)

    def check(self, mods, ruleset=0, **changes):
        return policy_module.check_score(self.policy(**changes), mods, ruleset, CATALOGS)[0]

    def test_cs9_and_optional_hd(self):
        self.assertTrue(self.check([dict(acronym="DA", settings=dict(circle_size=9))]))
        self.assertTrue(self.check([dict(acronym="DA", settings=dict(circle_size=9)), dict(acronym="HD")]))

    def test_settings_cannot_be_removed_or_changed(self):
        for settings in ({}, dict(circle_size=8), dict(circle_size=True), dict(circle_size=float("nan")), dict(circle_size=9, approach_rate=8)):
            with self.subTest(settings=settings):
                self.assertFalse(self.check([dict(acronym="DA", settings=settings)]))
        self.assertFalse(self.check([]))

    def test_unlisted_mods_rejected_including_empty_optional(self):
        self.assertFalse(self.check([dict(acronym="DA", settings=dict(circle_size=9)), dict(acronym="RX")]))
        self.assertFalse(self.check([dict(acronym="DA", settings=dict(circle_size=9)), dict(acronym="HD")], optional=[]))

    def test_hr_is_not_optional_with_da(self):
        with self.assertRaises(ValueError):
            self.policy(optional=["HR"])
        self.assertFalse(self.check([dict(acronym="DA", settings=dict(circle_size=9)), dict(acronym="HR")], allow_other_mods=True))

    def test_allow_compatible_extras(self):
        self.assertTrue(self.check([dict(acronym="DA", settings=dict(circle_size=9)), dict(acronym="RX")], allow_other_mods=True))

    def test_wrong_mode_and_duplicate_mods(self):
        self.assertFalse(self.check([dict(acronym="DA", settings=dict(circle_size=9))], ruleset=3))
        self.assertFalse(self.check([dict(acronym="DA", settings=dict(circle_size=9))] * 2))

    def test_invalid_policy(self):
        for changes in (dict(version=2), dict(optional=["FAKE"]), dict(required=[dict(acronym="DA", settings=dict(made_up=9))]), dict(required=[dict(acronym="DA", settings=dict(circle_size=float("inf")))]), dict(optional=["HD", "HD"])):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.policy(**changes)

    def test_nomod_means_no_mods(self):
        self.assertTrue(self.check([], required=[], optional=[]))
        self.assertFalse(self.check([dict(acronym="HD")], required=[], optional=[]))

    def test_nofail_is_optional_without_being_selected(self):
        mods = [dict(acronym="DA", settings=dict(circle_size=9)), dict(acronym="NF")]
        self.assertTrue(self.check(mods, optional=[]))
        self.assertTrue(self.check(mods[:1], optional=[]))
        self.assertTrue(self.check([dict(acronym="NF")], required=[], optional=[]))
        self.assertFalse(self.check([dict(acronym="NF")], optional=[]))
        self.assertFalse(self.check([dict(acronym="DA", settings=dict(circle_size=8)), dict(acronym="NF")], optional=[]))

    def test_nofail_does_not_replace_sd_or_pf(self):
        for acronym in ("SD", "PF"):
            with self.subTest(acronym=acronym):
                self.assertFalse(self.check([dict(acronym=acronym), dict(acronym="NF")], required=[dict(acronym=acronym)], optional=[]))

    def test_explicitly_required_nofail_stays_required(self):
        self.assertTrue(self.check([dict(acronym="NF")], required=[dict(acronym="NF")], optional=[]))
        self.assertFalse(self.check([], required=[dict(acronym="NF")], optional=[]))

    def test_required_rate_mods_allow_speed_and_pitch_changes(self):
        for name, speed in (("DT", 1.2), ("DT", 2.0), ("HT", 0.5), ("HT", 0.9)):
            with self.subTest(name=name, speed=speed):
                required = [dict(acronym=name, settings=dict(speed_change=1.5 if name == "DT" else 0.75))]
                for pitch in (True, False):
                    self.assertTrue(self.check([dict(acronym=name, settings=dict(speed_change=speed, adjust_pitch=pitch))], required=required, optional=[]))
                self.assertTrue(self.check([dict(acronym=name)], required=required, optional=[]))
                self.assertFalse(self.check([], required=required, optional=[]))

    def test_required_rate_mods_reject_invalid_settings(self):
        for name in ("DT", "HT"):
            for settings in (dict(speed_change=True), dict(speed_change=float("nan")), dict(speed_change=0), dict(speed_change=3), dict(adjust_pitch=1), dict(made_up=1)):
                with self.subTest(name=name, settings=settings):
                    self.assertFalse(self.check([dict(acronym=name, settings=settings)], required=[dict(acronym=name)], optional=[]))

    def test_rate_flexibility_does_not_unlock_da(self):
        required = [dict(acronym="DT"), dict(acronym="DA", settings=dict(circle_size=9))]
        for cs, allowed in ((9, True), (8, False)):
            self.assertEqual(self.check([dict(acronym="DT", settings=dict(speed_change=1.2)), dict(acronym="DA", settings=dict(circle_size=cs))], required=required, optional=[]), allowed)

    def test_required_pitch_adjust_is_not_replaced_by_rate_pitch(self):
        for name in ("DT", "HT"):
            required = [dict(acronym=name), dict(acronym="PA")]
            self.assertTrue(self.check(required, required=required, optional=[]))
            self.assertFalse(self.check([dict(acronym=name, settings=dict(adjust_pitch=True)), dict(acronym="PA")], required=required, optional=[]))


if __name__ == "__main__":
    unittest.main()
