from __future__ import annotations

import re

# Keywords triggering a hard regulatory refusal per Fin's Invariant 4
REFUSAL_TRIGGERS = [
    r"\bwhich\b.*\b(?:better|best)\b",
    r"\bbest\s+(?:plan|policy|term|health|insurance)\b",
    r"\bshould\s+i\s+(?:buy|choose|pick|take|get)\b",
    r"\brecommend(?:ation)?\b",
    r"\bwhich\s+should\s+i\b",
    r"\bcompare\b",
    r"\bbetter\s+than\b",
    r"\brank(?:ing)?\b",
    r"\bscore\s+this\b",
    r"\bvs\.?\b",
    r"\bversus\b",
]

REFUSAL_MESSAGE = (
    "Fin provides factual lookup of policy documents only. We do not compare, "
    "rank, score, or recommend insurance products. For personalized advice, "
    "consult a licensed SEBI RIA or IRDAI-registered insurance broker."
)


def evaluate_guardrail(query: str) -> tuple[bool, str | None]:
    """
    Check if a user query attempts to request insurance comparison, ranking, or advice.
    Returns (is_allowed, refusal_message_or_none).
    """
    lower_query = query.lower()
    for pattern in REFUSAL_TRIGGERS:
        if re.search(pattern, lower_query):
            return False, REFUSAL_MESSAGE
    return True, None
