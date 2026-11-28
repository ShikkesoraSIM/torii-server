import unittest

from app.database.torii_sub_profile import ToriiSubProfile


class SubProfilePolicyTest(unittest.TestCase):
    def profile(self, **policy):
        return ToriiSubProfile(master_user_id=1, profile_user_id=2, name="Test", tag="DT", **policy)

    def test_unknown_mode_is_rejected(self):
        self.assertFalse(self.profile(restriction_mode="typo").validate_score_mods([])[0])

    def test_free_profile_still_accepts_mods(self):
        self.assertTrue(self.profile(restriction_mode="free").validate_score_mods(["HD"])[0])

    def test_dt_accepts_nightcore(self):
        profile = self.profile(restriction_mode="dt_only")
        self.assertTrue(profile.validate_score_mods(["NC"])[0])
        self.assertFalse(profile.validate_score_mods([])[0])

    def test_custom_normalizes_stored_acronyms(self):
        profile = self.profile(restriction_mode="custom", required_mods='[" dt "]', allowed_mods='["hd"]')
        self.assertTrue(profile.validate_score_mods(["NC", "HD"])[0])
        self.assertFalse(profile.validate_score_mods(["NC", "HR"])[0])

    def test_custom_rejects_malformed_stored_policy(self):
        for raw in ('{', '{}', 'null', '[1]', '[""]'):
            with self.subTest(raw=raw):
                profile = self.profile(restriction_mode="custom", required_mods=raw)
                self.assertFalse(profile.validate_score_mods([])[0])

    def test_custom_disallowed_mod_is_rejected(self):
        profile = self.profile(restriction_mode="custom", disallowed_mods='["hr"]')
        self.assertFalse(profile.validate_score_mods(["HR"])[0])


if __name__ == "__main__":
    unittest.main()
