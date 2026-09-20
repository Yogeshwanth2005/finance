from app.services.rag.rag import clean_text, extract_text, chunk_text, embed, cosine
from app.services.rag.guardrails import evaluate_guardrail


def test_clean_text():
    raw = "<p>Hello <b>World</b> &amp; Fin</p>\n\n   Extra spaces   "
    assert clean_text(raw) == "Hello World & Fin Extra spaces"


def test_extract_text_txt():
    sample = b"Policy wording line 1\nPolicy wording line 2"
    extracted = extract_text("policy.txt", sample)
    assert "Policy wording line 1 Policy wording line 2" == extracted


def test_chunk_text():
    words = " ".join([f"word{i}" for i in range(100)])
    chunks = chunk_text(words, size=50, overlap=10)
    assert len(chunks) == 3
    assert "word0" in chunks[0]
    assert "word49" in chunks[0]
    # Check overlap
    assert "word40" in chunks[1]


def test_embed_and_cosine():
    vec1 = embed("hdfc ergo optima secure health insurance")
    vec2 = embed("hdfc ergo optima secure waiting period")
    vec3 = embed("completely unrelated mutual fund query")

    assert len(vec1) == 128
    sim_close = cosine(vec1, vec2)
    sim_far = cosine(vec1, vec3)
    assert sim_close > sim_far


def test_guardrails_refusal():
    # Disallowed queries
    disallowed = [
        "Which plan is better for me?",
        "Should I buy HDFC Ergo or ICICI Lombard?",
        "Recommend the best term insurance policy",
        "Compare Max Life vs Tata AIA",
    ]
    for q in disallowed:
        allowed, msg = evaluate_guardrail(q)
        assert allowed is False
        assert msg is not None
        assert "do not compare" in msg

    # Allowed factual queries
    allowed_queries = [
        "What is the waiting period for pre-existing diseases in Optima Secure?",
        "Does this policy cover robotic surgery?",
        "What are the exclusions under section 4.2?",
        "How do I file a cashless claim?",
    ]
    for q in allowed_queries:
        allowed, msg = evaluate_guardrail(q)
        assert allowed is True
        assert msg is None
