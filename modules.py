from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List


def build_clarification_questions(profile: Dict[str, Any]) -> List[str]:
    """Return the top missing fields that should be clarified before final recommendations."""
    questions = []
    if not profile.get("state"):
        questions.append("Which state are you applying from? (for example: Tamil Nadu, Karnataka, Delhi)")
    if not profile.get("age"):
        questions.append("What is your age group or age range?")
    if not profile.get("education"):
        questions.append("What is your current education level or course status?")
    if not profile.get("income"):
        questions.append("Do you want schemes based on income category or family income?")
    if not profile.get("occupation"):
        questions.append("Are you a student, employed person, job seeker, or entrepreneur?")
    return questions[:5]


def sort_schemes_by_deadline(schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return schemes sorted by deadline, earliest first. Missing dates are pushed to the end."""
    def parse_deadline(item: Dict[str, Any]):
        candidate = item.get("deadline") or item.get("last_date") or "9999-12-31"
        try:
            return datetime.strptime(str(candidate), "%Y-%m-%d").date()
        except ValueError:
            return datetime.strptime("9999-12-31", "%Y-%m-%d").date()

    return sorted(schemes, key=lambda item: parse_deadline(item))


def extract_vacancy_summary(query: str, schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return vacancy-like openings from the scheme list based on the user's query."""
    q = (query or "").lower()
    query_tokens = set(re.findall(r"[a-z]+", q))
    results = []

    for scheme in schemes:
        text = " ".join([
            scheme.get("name", ""),
            scheme.get("category", ""),
            " ".join(scheme.get("keywords", [])),
            scheme.get("description", "")
        ]).lower()
        score = len(query_tokens.intersection(set(re.findall(r"[a-z]+", text))))
        if score > 0 or any(word in text for word in ["vacancy", "job", "recruitment", "opening", "placement", "employment"]):
            results.append({
                "name": scheme.get("name", "Unknown scheme"),
                "category": scheme.get("category", "General"),
                "match_score": min(95, score * 20 + 10),
                "url": scheme.get("url", "")
            })
    return sorted(results, key=lambda item: item["match_score"], reverse=True)[:5]


def detect_media_type(file_name: str) -> str:
    """Return the media type for an uploaded file."""
    if not file_name:
        return "unknown"
    name = file_name.lower()
    if name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return "image"
    if name.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
        return "video"
    if name.endswith((".mp3", ".wav", ".ogg", ".m4a")):
        return "audio"
    if name.endswith((".pdf", ".txt", ".doc", ".docx")):
        return "document"
    return "file"


def build_profile_from_form(form_values: Dict[str, Any]) -> Dict[str, Any]:
    profile = {
        "state": (form_values.get("state") or "").strip(),
        "age": (form_values.get("age") or "").strip(),
        "education": (form_values.get("education") or "").strip(),
        "income": (form_values.get("income") or "").strip(),
        "occupation": (form_values.get("occupation") or "").strip(),
        "gender": (form_values.get("gender") or "").strip(),
        "disability": (form_values.get("disability") or "").strip(),
    }
    return profile


def generate_deadline_summary(schemes: List[Dict[str, Any]]) -> str:
    ordered = sort_schemes_by_deadline(schemes)
    if not ordered:
        return "No deadlines available in the current shortlist."
    lines = [f"{item.get('name', 'Scheme')} — {item.get('deadline', item.get('last_date', 'No date given'))}" for item in ordered[:3]]
    return " | ".join(lines)


def compare_scheme_features(schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a lightweight comparison summary for up to 5 schemes."""
    out = []
    for scheme in schemes[:5]:
        out.append({
            "name": scheme.get("name", "Unknown"),
            "category": scheme.get("category", "General"),
            "benefit": scheme.get("benefits", "Check official portal"),
            "match_score": scheme.get("match_score", 0),
            "url": scheme.get("url", "")
        })
    return out


def build_dashboard_summary(schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a board-style summary used by the premium dashboard."""
    if not schemes:
        return {
            "total_matches": 0,
            "top_match": "No recommendation yet",
            "next_deadline": "No deadline available",
            "avg_score": 0,
        }

    ordered = sort_schemes_by_deadline(schemes)
    highest = max(schemes, key=lambda x: x.get("match_score", 0))
    avg_score = round(sum(item.get("match_score", 0) for item in schemes) / len(schemes), 1)

    next_deadline = ordered[0].get("deadline", ordered[0].get("last_date", "No date available"))
    return {
        "total_matches": len(schemes),
        "top_match": highest.get("name", "Unknown"),
        "next_deadline": f"deadline: {next_deadline}",
        "avg_score": avg_score,
    }
