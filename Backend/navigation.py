"""Resolve spoken navigation requests against saved places."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


FUZZY_MATCH_THRESHOLD = 0.86
AMBIGUOUS_SCORE_GAP = 0.02

COMMAND_PREFIXES = (
    "navigate to",
    "directions to",
    "take me to",
    "please take me to",
    "can you take me to",
    "i want to go to",
    "show me the way to",
    "go to",
    "請帶我去",
    "请带我去",
    "請帶我到",
    "请带我到",
    "幫我導航到",
    "帮我导航到",
    "帶我去",
    "带我去",
    "帶我到",
    "带我到",
    "帶我",
    "带我",
    "導航到",
    "导航到",
    "導航去",
    "导航去",
    "我要去",
    "路線到",
    "路线到",
    "前往",
    "去",
)

POLITE_SUFFIXES = (
    "please",
    "謝謝",
    "谢谢",
    "好嗎",
    "好吗",
)


def normalize_navigation_text(value: str) -> str:
    """Normalize text while preserving language-specific letters and accents."""
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    characters = []
    for character in normalized:
        category = unicodedata.category(character)
        characters.append(character if category[0] in {"L", "N"} else " ")
    return " ".join("".join(characters).split())


def fold_diacritics(value: str) -> str:
    """Return a diacritic-free representation for Latin-script STT variants."""
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )


def extract_destination_query(utterance: str) -> str:
    """Remove a known voice-command wrapper and return the destination phrase."""
    query = normalize_navigation_text(utterance)
    for prefix in sorted(COMMAND_PREFIXES, key=len, reverse=True):
        normalized_prefix = normalize_navigation_text(prefix)
        if query == normalized_prefix:
            return ""
        if query.startswith(f"{normalized_prefix} ") or (
            _contains_cjk(normalized_prefix) and query.startswith(normalized_prefix)
        ):
            query = query[len(normalized_prefix) :].strip()
            break

    for suffix in sorted(POLITE_SUFFIXES, key=len, reverse=True):
        normalized_suffix = normalize_navigation_text(suffix)
        if query.endswith(f" {normalized_suffix}") or (
            _contains_cjk(normalized_suffix) and query.endswith(normalized_suffix)
        ):
            query = query[: -len(normalized_suffix)].strip()
            break
    return query


def resolve_destination(utterance: str, places: list[dict]) -> dict:
    """Return saved_place, ambiguous or not_found for a spoken utterance."""
    query = extract_destination_query(utterance)
    if not query:
        return {
            "status": True,
            "matchType": "not_found",
            "query": query,
            "destination": None,
        }

    normalized_utterance = normalize_navigation_text(utterance)
    folded_query = fold_diacritics(query)
    folded_utterance = fold_diacritics(normalized_utterance)
    matches = []

    for place in places:
        best = None
        labels = [place.get("name", ""), *(place.get("aliases") or [])]
        for label in labels:
            normalized_label = normalize_navigation_text(label)
            if not normalized_label:
                continue
            folded_label = fold_diacritics(normalized_label)
            score = _match_score(
                query=query,
                folded_query=folded_query,
                utterance=normalized_utterance,
                folded_utterance=folded_utterance,
                label=normalized_label,
                folded_label=folded_label,
            )
            if score is None:
                continue
            candidate = {
                "score": score,
                "matchedText": str(label).strip(),
                "place": place,
            }
            if best is None or candidate["score"] > best["score"]:
                best = candidate
        if best is not None:
            matches.append(best)

    if not matches:
        return {
            "status": True,
            "matchType": "not_found",
            "query": query,
            "destination": None,
        }

    matches.sort(
        key=lambda item: (
            -item["score"],
            normalize_navigation_text(item["place"].get("name", "")),
            item["place"].get("id", 0),
        )
    )
    best_score = matches[0]["score"]
    competing = [
        item
        for item in matches
        if best_score - item["score"] <= AMBIGUOUS_SCORE_GAP
    ]

    if len(competing) > 1:
        return {
            "status": True,
            "matchType": "ambiguous",
            "query": query,
            "confidence": round(best_score, 3),
            "candidates": [_public_place(item["place"]) for item in competing],
        }

    match = matches[0]
    return {
        "status": True,
        "matchType": "saved_place",
        "confidence": round(match["score"], 3),
        "matchedText": match["matchedText"],
        "destination": _public_place(match["place"]),
    }


def _match_score(
    *,
    query: str,
    folded_query: str,
    utterance: str,
    folded_utterance: str,
    label: str,
    folded_label: str,
) -> float | None:
    if query == label:
        return 1.0
    if folded_query == folded_label:
        return 0.98

    # Multi-word aliases can safely match inside a longer natural-language request.
    if " " in label and _contains_phrase(utterance, label):
        return min(0.97, 0.92 + len(label.split()) * 0.01)
    if " " in folded_label and _contains_phrase(folded_utterance, folded_label):
        return min(0.95, 0.90 + len(folded_label.split()) * 0.01)

    # Fuzzy matching is intentionally disabled for very short labels.
    if min(len(folded_query), len(folded_label)) < 4:
        return None
    similarity = SequenceMatcher(None, folded_query, folded_label).ratio()
    if similarity < FUZZY_MATCH_THRESHOLD:
        return None
    return min(0.89, 0.86 + (similarity - FUZZY_MATCH_THRESHOLD) * 0.2)


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?:^|\s){re.escape(phrase)}(?:$|\s)", text) is not None


def _contains_cjk(value: str) -> bool:
    return any("\u3400" <= character <= "\u9fff" for character in value)


def _public_place(place: dict) -> dict:
    return {
        key: value
        for key, value in place.items()
        if key in {"id", "name", "address", "lat", "lng"}
    }
