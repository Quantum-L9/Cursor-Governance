"""Tests for closed-chat word archive (no AWS required)."""

from __future__ import annotations

import json
from pathlib import Path

from ops.graphiti.hydration.archive_transcript import build_document, extract_turns, object_key


def test_extract_turns_keeps_words_and_timestamp(tmp_path: Path):
    path = tmp_path / "chat.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "role": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "<timestamp>Thursday, Aug 13, 2026, "
                                        "2:51 PM (UTC-4)</timestamp>\n"
                                        "<git_status>\nGit repo: /tmp/x\n</git_status>\n"
                                        "<user_query>\nfix the bucket lifecycle\n</user_query>"
                                    ),
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "role": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "I'll set Intelligent-Tiering and no expiration.",
                                },
                                {
                                    "type": "tool_use",
                                    "name": "Shell",
                                    "input": {"command": "aws s3 ls"},
                                },
                            ]
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    turns = extract_turns(path)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[0]["text"] == "fix the bucket lifecycle"
    assert "Aug 13, 2026" in (turns[0]["at"] or "")
    assert turns[1]["role"] == "assistant"
    assert "Intelligent-Tiering" in turns[1]["text"]
    assert "aws s3 ls" not in turns[1]["text"]


def test_object_key_and_document_meta(tmp_path: Path):
    path = tmp_path / "c.jsonl"
    path.write_text(
        json.dumps(
            {
                "role": "user",
                "message": {"content": [{"type": "text", "text": "<user_query>hi</user_query>"}]},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    turns = extract_turns(path)
    doc = build_document(
        conversation_id="abc-123",
        source_path=path,
        project_dir=str(tmp_path),
        turns=turns,
        host="mac-mini",
    )
    assert doc["schema"] == "l9-chat-transcript/v1"
    assert doc["conversation_id"] == "abc-123"
    assert doc["parent_conversation_id"] is None
    assert doc["source_mtime"]
    assert doc["source_bytes"] == path.stat().st_size
    assert doc["host"] == "mac-mini"
    assert doc["turn_count"] == 1
    assert object_key("abc-123") == "v1/abc-123.json"
