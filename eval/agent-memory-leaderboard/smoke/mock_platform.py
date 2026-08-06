"""Standalone smoke test: exercises the Add -> Search contract against a
running adapter, mimicking what the leaderboard platform does.

Usage:
    python smoke/mock_platform.py [BASE_URL]

Defaults to http://localhost:8080. Set MEMORY_API_KEY to test authenticated
mode. Exits non-zero on any contract violation.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
KEY = os.getenv("MEMORY_API_KEY")


def _post(path: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}
    )
    if KEY:
        req.add_header("X-Api-Key", KEY)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode("utf-8") or "{}")


def _get(path: str) -> tuple[int, dict]:
    with urllib.request.urlopen(BASE + path, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    run = "run_smoke"
    user = f"eval:{run}:locomo:conv-0"
    session = f"eval:{run}:sample:0"

    # 1) health
    status, body = _get("/health")
    if status != 200:
        _fail(f"/health returned {status}")
    print(f"health: {body}")

    # 2) add several memories
    memories = [
        "Alice adopted a golden retriever named Max in March 2024.",
        "Alice works as a marine biologist studying coral reefs in Australia.",
        "Bob is Alice's brother and lives in Toronto.",
        "Alice's favorite programming language is Python.",
    ]
    for i, text in enumerate(memories):
        req_id = f"eval:{run}:locomo_refined:conv-0:chunk-{i}"
        status, body = _post(
            "/add",
            {
                "request_id": req_id,
                "messages": [
                    {"role": "user", "timestamp": 1704067200000 + i, "content": text}
                ],
                "user_id": user,
                "session_id": session,
            },
        )
        if status != 200:
            _fail(f"/add chunk-{i} returned {status}: {body}")
        if body.get("success") is not True:
            _fail(f"/add chunk-{i} success != true: {body}")
        for field, expected in (
            ("request_id", req_id),
            ("user_id", user),
            ("session_id", session),
        ):
            if body.get(field) != expected:
                _fail(f"/add chunk-{i} {field} mis-echoed: {body}")
    print(f"add: stored {len(memories)} memories (synchronous)")

    # 3) search — must surface the relevant memory
    status, body = _post(
        "/search",
        {
            "query": "What pet does Alice have?",
            "user_id": user,
            "top_k": 100,
        },
    )
    if status != 200:
        _fail(f"/search returned {status}: {body}")
    data = body.get("data")
    if not isinstance(data, list) or not data:
        _fail(f"/search returned empty or malformed data: {body}")
    for item in data:
        if not item.get("id") or not item.get("content"):
            _fail(f"/search item missing id/content: {item}")
    if len(data) > 100:
        _fail(f"/search returned more than top_k items: {len(data)}")
    top = data[0]["content"].lower()
    if "max" not in top and "retriever" not in top:
        print(f"WARN: top result may be off-target: {data[0]['content']!r}")
    print(f"search: top result = {data[0]['content']!r}")

    # 4) choice question with options
    status, body = _post(
        "/search",
        {
            "query": "Which best describes Alice's profession?",
            "options": ["A. Software engineer", "B. Marine biologist", "C. Teacher"],
            "user_id": user,
            "top_k": 100,
        },
    )
    if status != 200 or not body.get("data"):
        _fail(f"/search (choice) failed: {status} {body}")

    # 5) isolation — a different user_id must NOT see Alice's memories
    status, body = _post(
        "/search",
        {"query": "What pet does Alice have?", "user_id": f"eval:{run}:locomo:conv-1", "top_k": 100},
    )
    if status != 200:
        _fail(f"/search isolation returned {status}: {body}")
    if body.get("data"):
        _fail(f"isolation breach: foreign user_id saw {len(body['data'])} memories")
    print("isolation: foreign user_id correctly sees no memories")

    print("\nSMOKE PASSED: Add -> Search contract satisfied.")


if __name__ == "__main__":
    main()
