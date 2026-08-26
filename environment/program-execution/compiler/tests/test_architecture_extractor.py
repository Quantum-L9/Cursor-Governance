"""The extractor boundary: chunking, provenance admission, and adapter safety."""

from __future__ import annotations

import json
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from compiler.architecture_extractor import (
    ArchitectureExtractorRequest,
    ArchitectureExtractorResponse,
    ClaudeCodeExtractor,
    DeterministicExtractor,
    ExtractorError,
    ExtractorUnavailable,
    chunk_units,
    new_request_id,
    parse_cli_payload,
    resolve_extractor,
)
from compiler.architecture_intent import load_architecture_intent, normalize_source, segment
from compiler.architecture_ir import admit, grounding_score

DOC = textwrap.dedent(
    """\
    # Provider authority

    DeepSeek MUST be the primary governed reasoning provider.

    Perplexity is research only and MUST NOT serve reasoning traffic.
    """
)


def _intent(tmp: Path, text: str = DOC):
    path = tmp / "arch.md"
    path.write_text(text, encoding="utf-8")
    return load_architecture_intent(path, target="Quantum-L9/LLM-Router", forced=True)


def _request(intent, mode: str = "extract") -> ArchitectureExtractorRequest:
    return ArchitectureExtractorRequest(
        request_id=new_request_id(),
        mode=mode,
        source_sha256=intent.sha256,
        units=intent.units,
        target=intent.target,
    )


class ChunkingTests(unittest.TestCase):
    def test_chunks_split_on_whole_units_and_lose_nothing(self) -> None:
        units = segment(
            normalize_source("\n\n".join(f"Paragraph {n} MUST hold." for n in range(60)))
        )
        chunks = chunk_units(units, max_chars=200)
        self.assertGreater(len(chunks), 1)
        flattened = [unit.id for chunk in chunks for unit in chunk]
        self.assertEqual(flattened, [unit.id for unit in units])
        self.assertEqual(len(flattened), len(set(flattened)), "no unit may appear twice")

    def test_a_unit_larger_than_the_budget_travels_whole(self) -> None:
        units = segment(normalize_source("MUST " + ("word " * 4000)))
        chunks = chunk_units(units, max_chars=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0][0].text, units[0].text)


class DeterministicExtractorTests(unittest.TestCase):
    def test_reads_obligations_and_cites_the_units_it_read(self) -> None:
        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            response = DeterministicExtractor().extract(_request(intent))
            kinds = {item["kind"] for item in response.items}
            self.assertIn("requirement", kinds)
            self.assertIn("prohibition", kinds)
            unit_ids = {unit.id for unit in intent.units}
            for item in response.items:
                self.assertLessEqual(set(item["source_refs"]), unit_ids)

    def test_its_own_statements_are_grounded_in_their_cited_units(self) -> None:
        """A self-inflicted ungrounded statement would be silently rejected."""
        with TemporaryDirectory() as raw:
            intent = _intent(
                Path(raw),
                DOC + "\n\nThe resolver lives in `src/matrices/capabilities.ts`"
                " and MUST be the only one.\n\n```bash\nnpm run verify:types\n```\n",
            )
            response = DeterministicExtractor().extract(_request(intent))
            texts = {unit.id: unit.text for unit in intent.units}
            accepted, rejected = admit(response.items, unit_texts=texts)
            self.assertEqual(rejected, [], msg=[item.to_dict() for item in rejected])
            self.assertTrue(accepted)

    def test_fence_delimiters_are_not_read_as_commands(self) -> None:
        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw), "# T\n\n```bash\nnpm test\n```\n")
            items = DeterministicExtractor().extract(_request(intent)).items
            commands = {item["statement"] for item in items if item["kind"] == "validation"}
            self.assertEqual(commands, {"npm test"})

    def test_a_prohibition_unit_quotes_its_prohibition_sentence(self) -> None:
        with TemporaryDirectory() as raw:
            intent = _intent(
                Path(raw),
                "# Budget\n\nDowngrade MUST remain in family. "
                "A task MUST NEVER land on a provider that cannot reason.\n",
            )
            items = DeterministicExtractor().extract(_request(intent)).items
            prohibition = next(item for item in items if item["kind"] == "prohibition")
            self.assertIn("MUST NEVER", prohibition["statement"])


class ResponseContractTests(unittest.TestCase):
    def test_malformed_response_is_refused_not_partially_admitted(self) -> None:
        with self.assertRaises(ExtractorError):
            ArchitectureExtractorResponse.from_dict({"items": [{"kind": "requirement"}]})
        with self.assertRaises(ExtractorError):
            ArchitectureExtractorResponse.from_dict("not an object")
        with self.assertRaises(ExtractorError):
            ArchitectureExtractorResponse.from_dict(
                {"items": [{"kind": "not_a_kind", "statement": "x", "source_refs": ["SRC-0001"]}]}
            )

    def test_cli_envelope_is_unwrapped_and_fences_tolerated(self) -> None:
        body = {"schema": "l9.program-execution.architecture-extractor-response.v1", "items": []}
        self.assertEqual(parse_cli_payload(json.dumps(body)), body)
        self.assertEqual(parse_cli_payload(json.dumps({"result": json.dumps(body)})), body)
        self.assertEqual(parse_cli_payload("```json\n" + json.dumps(body) + "\n```"), body)
        with self.assertRaises(ExtractorError):
            parse_cli_payload("")
        with self.assertRaises(ExtractorError):
            parse_cli_payload("I could not comply.")


class ClaudeAdapterTests(unittest.TestCase):
    def test_invocation_is_argv_read_only_and_bounded(self) -> None:
        adapter = ClaudeCodeExtractor()
        if not adapter.available():
            self.skipTest("claude executable is not on PATH")
        argv = adapter._argv("extract")
        self.assertNotIn("--dangerously-skip-permissions", argv)
        self.assertIn("--print", argv)
        self.assertIn("--permission-mode", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "plan")
        denied = argv[argv.index("--disallowed-tools") + 1]
        for tool in ("Bash", "Edit", "Write", "WebFetch"):
            self.assertIn(tool, denied)
        self.assertTrue(all(isinstance(part, str) for part in argv))
        self.assertGreater(adapter.timeout_seconds, 0)
        self.assertGreater(adapter.max_output_bytes, 0)

    def test_the_system_contract_declares_source_text_to_be_data(self) -> None:
        from compiler.architecture_extractor import EXTRACTOR_SYSTEM_CONTRACT

        lowered = EXTRACTOR_SYSTEM_CONTRACT.lower()
        self.assertIn("data", lowered)
        self.assertIn("never execute", lowered.replace("must never execute", "never execute"))

    def test_unknown_extractor_selection_fails_closed(self) -> None:
        with self.assertRaises(ExtractorUnavailable):
            resolve_extractor("no-such-extractor")

    def test_deterministic_selection_is_explicit(self) -> None:
        self.assertIsInstance(resolve_extractor("deterministic"), DeterministicExtractor)


class GroundingTests(unittest.TestCase):
    def test_a_faithful_reading_scores_far_above_an_invention(self) -> None:
        source = "Perplexity is research only. It MUST NOT serve reasoning traffic."
        faithful = grounding_score("Perplexity MUST NOT serve reasoning traffic.", [source])
        invented = grounding_score("Perplexity is the primary reasoning provider.", [source])
        unrelated = grounding_score("Delete the production database.", [source])
        self.assertGreater(faithful, invented)
        self.assertGreater(invented, unrelated)
        self.assertEqual(unrelated, 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
