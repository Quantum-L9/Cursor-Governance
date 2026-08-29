"""Architecture Intent v1: deterministic segmentation, identity, and signals."""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from compiler.architecture_intent import (
    ARCHITECTURE_INTENT_SCHEMA,
    ArchitectureIntentError,
    architecture_campaign_id,
    digest,
    load_architecture_intent,
    normalize_source,
    normative_signals,
    segment,
    slugify,
)

DOC = textwrap.dedent(
    """\
    # Router microscope

    DeepSeek MUST be the primary governed reasoning provider.

    - Perplexity is research only and MUST NOT serve reasoning traffic.
    - Budget downgrade stays within the capability family.

    | Field | Meaning |
    |---|---|
    | requiresReasoning | canonical capability authority |

    ```bash
    npm test
    npm run lint
    ```

    > Composite research plus reasoning is OUT OF SCOPE for this release.

    Plain context with no obligation in it at all.
    """
)


def _write(tmp: Path, text: str, name: str = "arch.md") -> Path:
    path = tmp / name
    path.write_text(text, encoding="utf-8")
    return path


class SegmentationTests(unittest.TestCase):
    def test_units_are_stable_across_identical_sources(self) -> None:
        first = segment(normalize_source(DOC))
        second = segment(normalize_source(DOC.replace("\n", "\r\n")))
        self.assertEqual(
            [(u.id, u.kind, u.line_start, u.line_end, u.sha256) for u in first],
            [(u.id, u.kind, u.line_start, u.line_end, u.sha256) for u in second],
            msg="CRLF is a normalization concern, not an identity change",
        )

    def test_structural_boundaries_are_respected(self) -> None:
        kinds = [unit.kind for unit in segment(normalize_source(DOC))]
        self.assertEqual(
            kinds,
            [
                "heading",
                "paragraph",
                "list_item",
                "list_item",
                "table",
                "code_fence",
                "blockquote",
                "paragraph",
            ],
        )

    def test_code_fence_is_one_unit_and_is_never_executed_material(self) -> None:
        fence = next(u for u in segment(normalize_source(DOC)) if u.kind == "code_fence")
        self.assertIn("npm test", fence.text)
        self.assertIn("npm run lint", fence.text)

    def test_material_source_change_changes_the_digest(self) -> None:
        base = normalize_source(DOC)
        edited = base.replace("DeepSeek MUST be", "DeepSeek MUST NOT be")
        self.assertNotEqual(digest(base), digest(edited))
        unit = next(u for u in segment(base) if "DeepSeek" in u.text)
        edited_unit = next(u for u in segment(edited) if "DeepSeek" in u.text)
        self.assertEqual(unit.id, edited_unit.id)
        self.assertNotEqual(unit.sha256, edited_unit.sha256)

    def test_normative_signals_retain_lowercase_material_prohibitions(self) -> None:
        self.assertEqual(normative_signals("The router must be fast."), ("MUST",))
        self.assertEqual(normative_signals("The router MUST be fast."), ("MUST",))
        self.assertIn("MUST NOT", normative_signals("It MUST NOT happen."))
        self.assertNotIn("MUST", normative_signals("It MUST NOT happen."))
        self.assertIn("DO NOT", normative_signals("don't replace assurance"))
        self.assertEqual(
            set(normative_signals("DO NOT REPLACE ASSURANCE")),
            set(normative_signals("do not replace assurance")),
        )
        self.assertEqual(normative_signals("Please keep going."), ())
        self.assertEqual(normative_signals("it deliberately never becomes one."), ())
        self.assertIn("NEVER", normative_signals("never replace assurance"))

    def test_line_spans_point_back_at_the_document(self) -> None:
        text = normalize_source(DOC)
        lines = text.split("\n")
        for unit in segment(text):
            self.assertEqual(unit.text, "\n".join(lines[unit.line_start - 1 : unit.line_end]))


class LoadingTests(unittest.TestCase):
    def test_raw_markdown_needs_no_frontmatter_when_forced(self) -> None:
        with TemporaryDirectory() as raw:
            path = _write(Path(raw), DOC)
            intent = load_architecture_intent(path, target="Quantum-L9/LLM-Router", forced=True)
            self.assertEqual(intent.schema, ARCHITECTURE_INTENT_SCHEMA)
            self.assertEqual(intent.target, "Quantum-L9/LLM-Router")
            self.assertFalse(intent.declared)
            self.assertEqual(intent.title, "Router microscope")

    def test_self_describing_document_carries_its_own_target(self) -> None:
        with TemporaryDirectory() as raw:
            path = _write(
                Path(raw),
                "---\n"
                f"schema: {ARCHITECTURE_INTENT_SCHEMA}\n"
                "target: Quantum-L9/SEO-Bot\n"
                "---\n\n" + DOC,
            )
            intent = load_architecture_intent(path, forced=False)
            self.assertTrue(intent.declared)
            self.assertEqual(intent.target, "Quantum-L9/SEO-Bot")
            self.assertEqual(intent.units[0].kind, "frontmatter")
            self.assertFalse(intent.units[0].normative)

    def test_undeclared_document_is_refused_without_the_forced_route(self) -> None:
        with TemporaryDirectory() as raw:
            path = _write(Path(raw), DOC)
            with self.assertRaises(ArchitectureIntentError) as ctx:
                load_architecture_intent(path, target="a/b", forced=False)
            self.assertIn(ARCHITECTURE_INTENT_SCHEMA, str(ctx.exception))

    def test_missing_target_fails_before_anything_else(self) -> None:
        with TemporaryDirectory() as raw:
            path = _write(Path(raw), DOC)
            with self.assertRaises(ArchitectureIntentError) as ctx:
                load_architecture_intent(path, forced=True)
            self.assertIn("target", str(ctx.exception))

    def test_unreadable_and_empty_sources_are_refused(self) -> None:
        with TemporaryDirectory() as raw:
            missing = Path(raw) / "nope.md"
            with self.assertRaises(ArchitectureIntentError):
                load_architecture_intent(missing, target="a/b", forced=True)
            empty = _write(Path(raw), "\n\n   \n", "empty.md")
            with self.assertRaises(ArchitectureIntentError):
                load_architecture_intent(empty, target="a/b", forced=True)


class CampaignIdTests(unittest.TestCase):
    def test_id_is_a_readable_slug_not_a_hash(self) -> None:
        with TemporaryDirectory() as raw:
            path = _write(Path(raw), DOC)
            intent = load_architecture_intent(path, target="a/b", forced=True)
            self.assertEqual(architecture_campaign_id(intent), "router-microscope-v1")

    def test_collision_is_answered_from_ids_that_exist(self) -> None:
        with TemporaryDirectory() as raw:
            path = _write(Path(raw), DOC)
            intent = load_architecture_intent(path, target="a/b", forced=True)
            taken = {"router-microscope-v1", "router-microscope-v2"}
            self.assertEqual(architecture_campaign_id(intent, taken), "router-microscope-v3")

    def test_slug_is_bounded_and_ascii(self) -> None:
        self.assertEqual(slugify("Résumé of the Röuter"), "resume-of-the-router")
        self.assertLessEqual(len(slugify("x" * 200)), 48)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
