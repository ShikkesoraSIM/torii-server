"""Versioned, configured mod restrictions. No database or application dependencies."""

import math
from copy import deepcopy


def validate_policy(policy: dict, catalogs: dict) -> dict:
    if not isinstance(policy, dict) or type(policy.get("version")) is not int or policy["version"] != 1:
        raise ValueError("Unsupported profile mod policy.")
    ruleset = policy.get("ruleset_id")
    if type(ruleset) is not int or ruleset not in catalogs:
        raise ValueError("Invalid profile game mode.")
    if type(policy.get("allow_other_mods")) is not bool:
        raise ValueError("Choose whether extra mods are allowed.")
    required = policy.get("required")
    optional = policy.get("optional")
    if not isinstance(required, list) or not isinstance(optional, list) or len(required) > 64 or len(optional) > 64:
        raise ValueError("Invalid profile mod list.")
    catalog = catalogs[ruleset]
    required_names = []
    for mod in required:
        if not isinstance(mod, dict):
            raise ValueError("Required mods must include an acronym and settings.")
        name = mod.get("acronym")
        if not isinstance(name, str) or name not in catalog or not catalog[name].get("UserPlayable"):
            raise ValueError("Unknown required mod.")
        if name in required_names:
            raise ValueError("Required mods cannot be repeated.")
        required_names.append(name)
        settings = mod.get("settings", {})
        definitions = {s["Name"]: s["Type"] for s in catalog[name]["Settings"]}
        if not isinstance(settings, dict):
            raise ValueError("Invalid mod settings.")
        for key, value in settings.items():
            kind = definitions.get(key)
            valid = (kind == "number" and type(value) in (int, float) and math.isfinite(value)
                     or kind == "boolean" and type(value) is bool
                     or kind == "string" and isinstance(value, str) and len(value) <= 256)
            if not valid:
                raise ValueError(f"Invalid setting for {name}: {key}.")
    if any(not isinstance(name, str) or name not in catalog or not catalog[name].get("UserPlayable") for name in optional):
        raise ValueError("Unknown optional mod.")
    if len(set(optional)) != len(optional) or set(optional).intersection(required_names):
        raise ValueError("A mod cannot be both required and optional.")

    def incompatible(left, right):
        return right in catalog[left]["IncompatibleMods"] or left in catalog[right]["IncompatibleMods"]

    for index, name in enumerate(required_names):
        if any(incompatible(name, other) for other in required_names[index + 1:]):
            raise ValueError("Required mods are incompatible with each other.")
        if any(incompatible(name, other) for other in optional):
            raise ValueError("Optional mods cannot replace a required mod.")
    return deepcopy(policy)


def check_score(policy: dict, mods: list, ruleset_id: int, catalogs: dict) -> tuple[bool, str | None]:
    if ruleset_id != policy["ruleset_id"]:
        return False, "This profile is restricted to a different game mode. Switch to Main to play it."
    if any(not isinstance(mod, dict) or not isinstance(mod.get("acronym"), str) for mod in mods):
        return False, "Invalid score mods."
    by_name = {mod["acronym"]: mod for mod in mods}
    if len(by_name) != len(mods):
        return False, "Duplicate score mods are not allowed."
    catalog = catalogs[ruleset_id]
    if any(name not in catalog for name in by_name):
        return False, "Unknown score mod."
    for name in by_name:
        other_mods = set(by_name) - {name}
        if set(catalog[name]["IncompatibleMods"]).intersection(other_mods):
            return False, "A score mod is incompatible with another mod on this score."
    for required in policy["required"]:
        name = required["acronym"]
        if name not in by_name:
            return False, f"This profile requires {name}."
        expected = required.get("settings", {})
        actual = by_name[name].get("settings", {})
        if name in ("DT", "HT"):
            if not isinstance(actual, dict):
                return False, f"Invalid settings for {name}."
            speed = actual.get("speed_change", 1.5 if name == "DT" else 0.75)
            lower, upper = (1.01, 2.0) if name == "DT" else (0.5, 0.99)
            if type(speed) not in (int, float) or not math.isfinite(speed) or not lower <= speed <= upper:
                return False, f"Invalid speed for {name}."
            if type(actual.get("adjust_pitch", False)) is not bool:
                return False, f"Invalid pitch setting for {name}."
            if actual.get("adjust_pitch", False) and "PA" in by_name:
                return False, "Pitch Adjust cannot be combined with rate-adjusted pitch."
            # DT/HT siguen obligatorios; velocidad y pitch quedan a eleccion.
            expected = {k: v for k, v in expected.items() if k not in ("speed_change", "adjust_pitch")}
            actual = {k: v for k, v in actual.items() if k not in ("speed_change", "adjust_pitch")}
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            return False, f"The settings for {name} are locked to this profile."
        for key, value in expected.items():
            other = actual[key]
            if type(value) in (int, float):
                equal = type(other) in (int, float) and math.isfinite(other) and math.isclose(value, other, rel_tol=0, abs_tol=1e-6)
            else:
                equal = type(value) is type(other) and value == other
            if not equal:
                return False, f"The setting {key} for {name} is locked to this profile."
    if not policy["allow_other_mods"]:
        allowed = {m["acronym"] for m in policy["required"]} | set(policy["optional"]) | {"NF"}
        if set(by_name) - allowed:
            return False, "This profile only allows its required and optional mods."
    return True, None
