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


class OneNormativeVocabularyTests(unittest.TestCase):
    """CE-AT-002 / CE-AT-003 on the live surface, not only in shadow.

    `architecture_intent.normative_signals` is the single source of normative
    lexical semantics. These prove the deterministic extractor now reads that
    vocabulary rather than a second, upper-case-only one of its own — the
    surface the tests actually force, and the one W4 left open.
    """

    def test_lowercase_prohibition_survives_with_provenance(self) -> None:
        """CE-AT-002. The 04_lowercase_prohibition sentence, read live."""
        with TemporaryDirectory() as raw:
            intent = _intent(
                Path(raw),
                "# Assurance\n\ndon't replace assurance. The existing "
                "`compiler/intent.py` must stay the parser.\n",
            )
            items = DeterministicExtractor().extract(_request(intent)).items
            kinds = {item["kind"] for item in items}
            self.assertIn("prohibition", kinds, msg=[i["statement"] for i in items])
            self.assertIn("requirement", kinds, msg=[i["statement"] for i in items])
            unit_ids = {unit.id for unit in intent.units}
            for item in items:
                self.assertTrue(item["source_refs"], msg=item)
                self.assertLessEqual(set(item["source_refs"]), unit_ids)

    def test_upper_and_lower_prohibitions_are_semantically_equivalent(self) -> None:
        """CE-AT-003. Case changes the wording, never the semantics."""
        extractor = DeterministicExtractor()
        for lower, upper in (
            ("it must not happen.", "It MUST NOT happen."),
            ("don't replace assurance.", "DO NOT replace assurance."),
            ("never replace assurance.", "NEVER replace assurance."),
            ("the parser must stay.", "The parser MUST stay."),
            ("preserve the existing router.", "PRESERVE the existing router."),
        ):
            with self.subTest(lower=lower):
                kind = extractor._sentence_kind(lower)
                self.assertEqual(
                    kind,
                    extractor._sentence_kind(upper),
                    msg=f"{lower!r} and {upper!r} must reach the same kind",
                )
                self.assertIsNotNone(kind)

    def test_material_keep_does_not_silently_disappear(self) -> None:
        """`normative_signals` calls this material, so a kind must accept it."""
        extractor = DeterministicExtractor()
        self.assertEqual(extractor._sentence_kind("keep the existing router."), "scope_include")

    def test_conversational_prose_is_still_not_an_obligation(self) -> None:
        """Collapsing the vocabularies must not drown coverage (C2 threshold)."""
        extractor = DeterministicExtractor()
        for prose in (
            "Please keep going.",
            "it deliberately never becomes one.",
            "risk of drift is acceptable here.",
            "a READONLY mount is fine.",
        ):
            with self.subTest(prose=prose):
                self.assertIsNone(extractor._sentence_kind(prose))


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


class TruncatedPayloadTests(unittest.TestCase):
    """A payload the runner cut off is refused as over budget, never parsed or
    reported as "returned no output"."""

    def _adapter(self) -> ClaudeCodeExtractor:
        adapter = ClaudeCodeExtractor()
        adapter._resolved = "/usr/bin/claude-fake"
        return adapter

    def _fake_result(self, *, stdout: str, truncated: bool, size: int):
        import peer_execution.subprocess_runner as runner

        return runner.CommandResult(
            argv=("claude-fake",),
            executable="/usr/bin/claude-fake",
            exit_code=0,
            stdout=stdout,
            stderr="",
            stdout_digest="sha256:" + "0" * 64,
            stderr_digest="sha256:" + "0" * 64,
            duration_seconds=0.1,
            timed_out=False,
            environment_fingerprint="sha256:test",
            stdout_truncated=truncated,
            stdout_bytes=size,
        )

    def test_a_truncated_runner_result_is_refused_as_over_budget(self) -> None:
        from unittest.mock import patch

        import peer_execution.subprocess_runner as runner

        with TemporaryDirectory() as raw:
            request = _request(_intent(Path(raw)))
        fake = self._fake_result(stdout='{"items": []', truncated=True, size=2_000_000)
        with patch.object(runner, "run_argv", return_value=fake):
            with self.assertRaises(ExtractorError) as ctx:
                self._adapter().extract(request)
        message = str(ctx.exception)
        self.assertIn("truncated", message)
        self.assertNotIn("returned no output", message)
        self.assertNotIn("not valid JSON", message)

    def test_a_complete_result_within_budget_is_still_parsed(self) -> None:
        from unittest.mock import patch

        import peer_execution.subprocess_runner as runner

        with TemporaryDirectory() as raw:
            request = _request(_intent(Path(raw)))
        payload = json.dumps({"request_id": request.request_id, "items": [], "notes": []})
        fake = self._fake_result(stdout=payload, truncated=False, size=len(payload))
        with patch.object(runner, "run_argv", return_value=fake):
            response = self._adapter().extract(request)
        self.assertEqual(response.items, ())
