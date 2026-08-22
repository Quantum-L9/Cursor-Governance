"""Tests for the raw-socket HTTP transport in ops/graphiti/graphiti_memory_client.py.

The client deliberately avoids ``urllib.urlopen`` (CWE-939) and speaks HTTP over
a socket it builds itself. That hand-rolled request is easy to get subtly wrong
in ways that look like the *server* being unavailable, which is exactly what
happened: the request was HTTP/1.0, the reverse proxy in front of the hosted
Graphiti server answered ``426 Upgrade Required``, and every session reported the
memory plane as DEGRADED while the server was healthy the whole time.

Two properties are pinned here, and they only make sense together:

* the request must be HTTP/1.1, or the proxy rejects it; and
* a chunked response must be de-framed, because HTTP/1.1 is what allows the
  server to chunk in the first place.

Fixing only the first turns a loud transport failure into a silent one: the body
comes back with chunk-size lines spliced through it.
"""

from __future__ import annotations

import sys
from email.message import Message
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "graphiti"))

import urllib.error  # noqa: E402

from graphiti_memory_client import _dechunk, _parse_http_response  # noqa: E402


def _response(headers: str, body: bytes) -> bytes:
    return ("HTTP/1.1 200 OK\r\n" + headers).encode("latin-1") + b"\r\n\r\n" + body


def test_request_line_is_http_1_1() -> None:
    """The version on the wire is the whole bug; 1.0 is what drew the 426.

    Only the request line is inspected. Searching the file for "HTTP/1.0" would
    also match the prose explaining why it is no longer used.
    """
    source = (REPO / "ops" / "graphiti" / "graphiti_memory_client.py").read_text(encoding="utf-8")
    request_lines = [
        line.strip() for line in source.splitlines() if "{method} {path} HTTP/" in line
    ]
    assert request_lines == ['f"{method} {path} HTTP/1.1",']


def _chunked(*pieces: bytes) -> bytes:
    """Frame pieces as a chunked body, so the test data cannot be miswritten."""
    out = b"".join(b"%x\r\n%s\r\n" % (len(piece), piece) for piece in pieces)
    return out + b"0\r\n\r\n"


def test_chunked_body_is_reassembled() -> None:
    """The server streams SSE across several chunks; the caller must see one body."""
    raw = _response(
        "Content-Type: text/event-stream\r\nTransfer-Encoding: chunked",
        _chunked(b"event: me", b"ssage\r\n"),
    )
    _status, _reason, _headers, body = _parse_http_response(raw)
    assert body == b"event: message\r\n"


def test_chunked_body_with_extension_is_reassembled() -> None:
    """A chunk size may carry a ``;ext`` suffix; it is not part of the size."""
    assert _dechunk(b"4;name=value\r\nokay\r\n0\r\n\r\n") == b"okay"


def test_content_length_body_is_still_honoured() -> None:
    """The non-chunked path must keep working; most replies still use it."""
    raw = _response("Content-Length: 4", b"okaytrailing-garbage")
    _status, _reason, _headers, body = _parse_http_response(raw)
    assert body == b"okay"


def test_unframed_body_is_read_to_end() -> None:
    """With neither header the body runs to EOF, which Connection: close gives."""
    raw = _response("Content-Type: application/json", b'{"status":"healthy"}')
    _status, _reason, _headers, body = _parse_http_response(raw)
    assert body == b'{"status":"healthy"}'


@pytest.mark.parametrize(
    "body,reason",
    [
        (b"4\r\nok", "truncated"),
        (b"zz\r\nokay\r\n0\r\n\r\n", "unparseable size"),
        (b"4", "ended mid-header"),
    ],
)
def test_malformed_chunked_bodies_raise(body: bytes, reason: str) -> None:
    """A short read must fail loudly rather than return a partial payload."""
    with pytest.raises(urllib.error.URLError):
        _dechunk(body)


def test_chunked_detection_is_case_insensitive() -> None:
    """Header casing is not guaranteed on the wire."""
    raw = _response("transfer-encoding: Chunked", _chunked(b"okay"))
    _status, _reason, headers, body = _parse_http_response(raw)
    assert isinstance(headers, Message)
    assert body == b"okay"
