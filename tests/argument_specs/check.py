"""Check each role's meta/argument_specs.yml against its defaults/main.yml.

For every role under roles/, the "main" entry point must:
- document every variable in defaults/main.yml, and nothing that isn't there;
- declare a type that literal (non-templated) defaults satisfy, including
  list elements and choices;
- mark non-bool options whose name ends in password, token or secret no_log.

Variables starting with "_" or containing "__" are internal and skipped.
Run from the repo root: python tests/argument_specs/check.py
"""
from __future__ import annotations

import pathlib
import sys

import yaml

SECRET_SUFFIXES = ("password", "token", "secret")
TYPES = {
    "str": (str,),
    "path": (str,),
    "int": (int,),
    "float": (int, float),
    "bool": (bool,),
    "list": (list,),
    "dict": (dict,),
}


def is_internal(name: str) -> bool:
    return name.startswith("_") or "__" in name


def is_templated(value) -> bool:
    return isinstance(value, str) and "{{" in value


def type_ok(value, type_name: str) -> bool:
    if type_name in ("raw", None):
        return True
    expected = TYPES.get(type_name)
    if expected is None:
        return True
    # bool is an int subclass; an int option must not accept true/false.
    if type_name in ("int", "float") and isinstance(value, bool):
        return False
    return isinstance(value, expected)


def check_role(role: pathlib.Path) -> list[str]:
    errors: list[str] = []
    spec_file = role / "meta" / "argument_specs.yml"
    defaults_file = role / "defaults" / "main.yml"
    if not spec_file.is_file():
        return [f"{role.name}: no meta/argument_specs.yml"]
    spec = yaml.safe_load(spec_file.read_text()) or {}
    main = (spec.get("argument_specs") or {}).get("main")
    if not main:
        return [f"{role.name}: argument_specs has no 'main' entry point"]
    options = main.get("options") or {}
    defaults = {}
    if defaults_file.is_file():
        defaults = yaml.safe_load(defaults_file.read_text()) or {}
    public = {k: v for k, v in defaults.items() if not is_internal(k)}

    for name in sorted(set(public) - set(options)):
        errors.append(f"{role.name}: default '{name}' is not in argument_specs")
    for name in sorted(set(options) - set(public)):
        if not options[name].get("required"):
            errors.append(f"{role.name}: argument_specs option '{name}' has no default and isn't required")

    for name, opt in sorted(options.items()):
        opt = opt or {}
        if not opt.get("description"):
            errors.append(f"{role.name}: option '{name}' has no description")
        # A bool switch such as *_manage_secret holds no secret.
        if name.endswith(SECRET_SUFFIXES) and opt.get("type", "str") != "bool" and not opt.get("no_log"):
            errors.append(f"{role.name}: option '{name}' looks secret but isn't no_log")
        if name not in public or is_templated(public[name]):
            continue
        value = public[name]
        type_name = opt.get("type", "str")
        if not type_ok(value, type_name):
            errors.append(f"{role.name}: default of '{name}' ({type(value).__name__}) doesn't match type {type_name}")
            continue
        elements = opt.get("elements")
        if type_name == "list" and elements:
            bad = [v for v in value if not is_templated(v) and not type_ok(v, elements)]
            if bad:
                errors.append(f"{role.name}: '{name}' has elements that aren't {elements}: {bad}")
        choices = opt.get("choices")
        # For a list, choices apply to each element.
        values = value if type_name == "list" else [value]
        if choices and any(v not in choices for v in values if v != ""):
            errors.append(f"{role.name}: default of '{name}' ({value!r}) isn't one of {choices}")
    return errors


def main() -> int:
    roles = sorted(p for p in pathlib.Path("roles").iterdir() if p.is_dir())
    if not roles:
        print("no roles/ found; run from the repo root")
        return 1
    errors = [e for role in roles for e in check_role(role)]
    for e in errors:
        print(f"ERROR: {e}")
    print(f"{len(roles)} roles checked, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
