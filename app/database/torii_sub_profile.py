import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlmodel import Column, BigInteger, Field, ForeignKey, SQLModel, String, Text


class ProfileRestrictionMode(StrEnum):
    FREE = "free"
    HD_ONLY = "hd_only"
    DT_ONLY = "dt_only"
    NOMOD_ONLY = "nomod_only"
    CUSTOM = "custom"


class ToriiSubProfile(SQLModel, table=True):
    __tablename__: str = "torii_sub_profiles"

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, autoincrement=True, primary_key=True),
    )
    master_user_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("lazer_users.id"), index=True, nullable=False),
    )
    profile_user_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("lazer_users.id"), unique=True, index=True, nullable=False),
    )
    name: str = Field(sa_column=Column(String(64), nullable=False))
    tag: str = Field(sa_column=Column(String(16), nullable=False))
    restriction_mode: str = Field(default=ProfileRestrictionMode.FREE, sa_column=Column(String(32), nullable=False))
    required_mods: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    allowed_mods: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    disallowed_mods: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    mod_policy: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    ruleset_id: int = Field(default=0)
    creation_key: str | None = Field(default=None, max_length=36, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def get_required_mods_list(self) -> list[str]:
        try:
            return json.loads(self.required_mods) or []
        except Exception:
            return []

    def get_allowed_mods_list(self) -> list[str]:
        try:
            return json.loads(self.allowed_mods) or []
        except Exception:
            return []

    def get_disallowed_mods_list(self) -> list[str]:
        try:
            return json.loads(self.disallowed_mods) or []
        except Exception:
            return []

    def validate_score_mods(self, score_mods: list[str] | list[dict], ruleset_id: int | None = None) -> tuple[bool, str | None]:
        """
        Validate whether score mods meet the policy for this profile.
        score_mods: list of mod acronyms (e.g. ["HD", "DT"]).
        Returns (is_valid, error_message).
        """
        if ruleset_id is not None and ruleset_id != self.ruleset_id:
            return False, "This profile belongs to another game mode. Switch to Main to play it."
        if self.mod_policy is not None:
            from app.models.mods import API_MODS
            from app.models.sub_profile_mod_policy import check_score, validate_policy

            try:
                policy = validate_policy(json.loads(self.mod_policy), API_MODS)
                return check_score(policy, score_mods, ruleset_id, API_MODS)
            except (ValueError, TypeError, KeyError):
                return False, "This profile has an invalid mod policy. Please contact support."
        mode = self.restriction_mode
        normalized_mods = {m.upper() if isinstance(m, str) else m.get("acronym", "").upper() for m in score_mods}

        if mode == ProfileRestrictionMode.FREE:
            return True, None

        if mode == ProfileRestrictionMode.HD_ONLY:
            if "HD" not in normalized_mods:
                return False, "This profile requires playing with the Hidden (HD) mod."
            return True, None

        if mode == ProfileRestrictionMode.DT_ONLY:
            if "DT" not in normalized_mods and "NC" not in normalized_mods:
                return False, "This profile requires playing with Double Time (DT) or Nightcore (NC)."
            return True, None

        if mode == ProfileRestrictionMode.NOMOD_ONLY:
            diff_mods = {"HD", "HR", "DT", "NC", "FL", "EZ", "HT"}
            present = normalized_mods.intersection(diff_mods)
            if present:
                return False, f"This is a NoMod profile. Difficulty mods are not allowed: {', '.join(present)}."
            return True, None

        if mode == ProfileRestrictionMode.CUSTOM:
            try:
                policies = []
                for raw in (self.required_mods, self.allowed_mods, self.disallowed_mods):
                    values = json.loads(raw)
                    if not isinstance(values, list) or any(not isinstance(m, str) or not m.strip() for m in values):
                        raise ValueError("Invalid mod policy")
                    policies.append({m.strip().upper() for m in values})
                req, allowed, dis = policies
            except (ValueError, TypeError):
                return False, "This profile has an invalid mod policy. Please contact support."

            for r in req:
                if r == "DT":
                    if "DT" not in normalized_mods and "NC" not in normalized_mods:
                        return False, "This profile requires Double Time (DT) or Nightcore (NC)."
                elif r not in normalized_mods:
                    return False, f"Missing required mod: {r}."

            forbidden = normalized_mods.intersection(dis)
            if forbidden:
                return False, f"The following mods are not permitted on this profile: {', '.join(forbidden)}."

            if allowed:
                valid_mods = req | allowed
                if "DT" in req or "DT" in allowed:
                    valid_mods.add("NC")
                extra = normalized_mods - valid_mods
                # Filter for difficulty/scoring mods
                diff_mods = {"HD", "HR", "DT", "NC", "FL", "EZ", "HT"}
                extra_diff = extra.intersection(diff_mods)
                if extra_diff:
                    return False, f"Additional difficulty mods are not allowed on this profile: {', '.join(extra_diff)}."

            return True, None

        return False, "This profile has an unknown restriction mode. Please contact support."
