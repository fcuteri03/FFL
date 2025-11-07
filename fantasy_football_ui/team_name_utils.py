"""Utility helpers for team name normalization."""

from typing import Optional


_TEAM_NAME_ALIASES = {
    "willbroda": "Willy",
    "dfitzzz87": "Fitz",
    "tkurosky12": "TK",
    "jsuperick": "Supe",
    "bobbddowns": "Bob",
    "acrayton": "Adam",
    "ccrealtor7": "CC",
    "dirtymike1414": "Dirty",
    "freddiec03": "Fred",
    "rickd1294": "Rich",
    "ahanula21": "Chud",
    "goodluck2u": "Mike",
    "jizzysnakeeyez": "Joe C",
    "lwallace12": "Wallace",
}


def normalize_team_name(name: Optional[str]) -> str:
    """Normalize raw team/display names to preferred aliases."""
    if not name:
        return "Unknown"

    lookup_key = name.lower()
    return _TEAM_NAME_ALIASES.get(lookup_key, name)
