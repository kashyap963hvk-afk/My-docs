"""Test the supervisor routing with fake agents (no LLM, no OpenSearch needed)."""
from querymesh import graph, skills

CHUNK = {"paper_id": "2401.00001", "title": "RRF", "text": "RRF adds 1/(60+rank).", "url": "u"}


def fake_skills(monkeypatch, relevant_after_scout=False, grounded_sequence=(True,)):
    calls = []
    grounded = list(grounded_sequence)
    scouted = {"done": False}

    def retrieve(query, k):
        calls.append("retrieve")
        return [CHUNK, CHUNK]

    def grade(question, chunks):
        calls.append("grade")
        return chunks if (not relevant_after_scout or scouted["done"]) else []

    def write(question, chunks, feedback=""):
        calls.append("write")
        return {"answer": "RRF merges rankings [1].", "citations": [{"n": 1, **CHUNK}]}

    def critic(question, answer, chunks):
        calls.append("critic")
        return {"grounded": grounded.pop(0), "feedback": "claim 2 unsupported"}

    def scout(topic, max_papers):
        calls.append("scout")
        scouted["done"] = True
        return {"added": ["2401.00002"]}

    monkeypatch.setattr(graph, "LOCAL_SKILLS", {"retrieve": retrieve, "grade": grade, "write": write,
                                                "critic": critic, "scout": scout})
    monkeypatch.setattr(skills, "rewrite_query", lambda q, p: "better query")
    return calls


async def test_happy_path(monkeypatch):
    calls = fake_skills(monkeypatch)
    result = await graph.ask("What is RRF?")
    assert calls == ["retrieve", "grade", "write", "critic"]
    assert result["grounded"] is True and result["citations"][0]["n"] == 1


async def test_retry_then_scout(monkeypatch):
    calls = fake_skills(monkeypatch, relevant_after_scout=True)
    await graph.ask("What is RRF?")
    assert calls == ["retrieve", "grade", "retrieve", "grade", "scout", "retrieve", "grade",
                     "write", "critic"]


async def test_rewrite_when_not_grounded(monkeypatch):
    calls = fake_skills(monkeypatch, grounded_sequence=(False, True))
    result = await graph.ask("What is RRF?")
    assert calls[-4:] == ["write", "critic", "write", "critic"]
    assert result["grounded"] is True
