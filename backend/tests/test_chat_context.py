"""Pure helpers behind the open (LLM-answers-everything) chat mode; no server, DB or network needed."""

from lib.chat_context import (
    SCOPE_RULES,
    build_retrieval_query,
    cited_titles,
    format_history,
    top_chunks_per_document,
)

HISTORY = [
    {"role": "you", "text": "Which plan gives me more coverage?"},
    {"role": "advisor", "text": "Secure Life Shield Policy has the higher sum assured."},
]


def test_short_follow_up_borrows_previous_user_question_for_retrieval():
    query = build_retrieval_query("which should I take", HISTORY)
    assert "more coverage" in query
    assert "which should I take" in query


def test_long_question_is_used_as_is():
    question = "Compare the premium and the waiting period of both term plans for my family"
    assert build_retrieval_query(question, HISTORY) == question


def test_short_question_without_history_is_used_as_is():
    assert build_retrieval_query("which should I take", []) == "which should I take"


def test_format_history_labels_roles_and_truncates():
    text = format_history([{"role": "you", "text": "a" * 2000}, {"role": "advisor", "text": "ok"}])
    lines = text.splitlines()
    assert lines[0].startswith("User: ") and len(lines[0]) < 700
    assert lines[1] == "Advisor: ok"


def test_cited_titles_only_lists_plans_the_answer_names():
    titles = ["Secure Life Shield Policy", "Retest Family Term Policy", "Secure Life Shield Policy"]
    answer = "I would pick the secure life shield policy because of its higher cover."
    assert cited_titles(answer, titles) == ["Secure Life Shield Policy"]
    assert cited_titles("Term insurance replaces income.", titles) == []


def test_scope_rules_cover_in_scope_topics_refusal_and_ambiguous_follow_ups():
    rules = SCOPE_RULES.lower()
    for topic in ("personal finance", "insurance", "surakshacfo", "profile"):
        assert topic in rules
    assert "outside" in rules and "do not answer" in rules
    assert "ignore" in rules  # resists "ignore your instructions"
    assert "which should i take" in rules  # ambiguous follow-ups stay in scope


def _chunk(doc, n):
    return {"document_id": doc, "text": f"{doc}-{n}"}


def test_top_chunks_per_document_keeps_every_plan_represented():
    scored = [(0.9, _chunk("a", 1)), (0.8, _chunk("a", 2)), (0.7, _chunk("a", 3)), (0.2, _chunk("b", 1))]
    picked = top_chunks_per_document(scored, per_document=2, max_documents=6)
    assert [c["text"] for c in picked] == ["a-1", "a-2", "b-1"]


def test_top_chunks_per_document_caps_number_of_documents_by_best_score():
    scored = [(0.9, _chunk("a", 1)), (0.5, _chunk("b", 1)), (0.3, _chunk("c", 1))]
    picked = top_chunks_per_document(scored, per_document=1, max_documents=2)
    assert [c["document_id"] for c in picked] == ["a", "b"]
