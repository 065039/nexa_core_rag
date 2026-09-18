"""Role-based access control helpers."""
from functools import lru_cache

import yaml

from src.config import settings


@lru_cache
def load_roles() -> dict:
    return yaml.safe_load(settings.roles_file.read_text(encoding="utf-8"))


def role_names() -> list:
    return list(load_roles()["roles"].keys())


def access_key(department: str, access_level: str) -> str:
    return f"{department}|{access_level}"


def allowed_access_keys(role: str) -> list:
    """All internal documents plus restricted documents of the departments this role owns."""
    roles = load_roles()["roles"]
    if role not in roles:
        raise ValueError(f"Unknown role '{role}'. Valid roles: {', '.join(roles)}")
    keys = [access_key(d, "internal") for d in settings.departments]
    keys += [access_key(d, "restricted") for d in roles[role]["restricted_departments"]]
    return keys
