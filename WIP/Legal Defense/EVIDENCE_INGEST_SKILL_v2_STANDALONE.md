# EVIDENCE INGEST SKILL v2 — Hardened
**DRAFT — PRO SE WORKING DOCUMENT. Not legal advice.**
Scope: converting raw evidence (bodycam video, audio, photos) into formats ingestible by this system, with chain-of-custody integrity preserved throughout. Applies to Case 26CR294791-170 and any future evidence batch.

---

## 0. Legal Gate — Check Before Any Processing

North Carolina restricts release of law-enforcement-held recordings: they may be released "only pursuant to court order," and the court may impose "any conditions or restrictions on the release ... that the court, in its discretion, deems appropriate" (N.C.G.S. § 132-1.4A).

Before step 1, answer and log:
- Source of this copy: [ ] § 132-1.4A court order [ ] Criminal discovery (§ 15A-903) [ ] Personal recording [ ] Other: ___
- If court order: re-read conditions attached to the order NOW. Any condition overrides this skill.
- If discovery: check for a § 15A-908 protective order restricting copying/dissemination.
- Confirm: no frame, clip, transcript excerpt, or filename will be posted, shared, or discussed outside counsel/court filings.

STOP if source is unknown or unconfirmed. Do not proceed to step 1.

---

## 1. Chain of Custody — Before Touching Anything

```bash
mkdir -p evidence/originals evidence/working evidence/derived evidence/logs
cd evidence/originals
shasum -a 256 * > ../logs/original_hashes_$(date +%Y%m%d_%H%M%S).txt
chmod 444 *
```

Rules:
- NEVER edit, rename, crop, rotate, color-correct, or re-encode files in `originals/`.
- All work happens on copies in `working/`.
- Every derived file gets logged in `logs/derivation_log.csv` with columns: `derived_filename, source_filename, source_hash, operation, timestamp_created, operator`.
- Re-hash `originals/` weekly and diff against the first log. Any mismatch = STOP, do not use, investigate immediately.

---

## 2. Inventory Manifest — First Output, Before Conversion

Before converting anything, produce `logs/evidence_manifest.csv`:

| filename | type | duration_or_pages | source | hash | date_recorded | date_received | notes |

Populate fully before touching step 3. This is what lets you (or anyone) answer "what do I actually have" without re-opening every file.

---

## 3. Video → Audio Extraction

```bash
cd evidence/working
ffmpeg -i ../originals/bodycam_01.mp4 -ar 16000 -ac 1 -vn bodycam_01_audio.wav
```
- `-ar 16000 -ac 1`: 16kHz mono, required format for Whisper.
- `-vn`: strips video, audio only.
- Log this operation in `derivation_log.csv` immediately.

---

## 4. Transcription — Whisper, Word-Level Timestamps

```bash
pip install -U openai-whisper
whisper bodycam_01_audio.wav --model large-v3 --word_timestamps True \
  --output_format json --output_dir ../derived/
```

Hardened rules (v2 additions):
- **Never treat raw Whisper output as final.** It hallucinates words in overlapping speech, mishears proper nouns, and can insert plausible-sounding but wrong dialogue — the single highest risk to credibility.
- Manual correction pass required. Any word you are not confident about: mark `[INAUDIBLE]`. Do not guess, do not "clean up" grammar, do not infer intent.
- Two-pass rule: transcribe once, walk away, re-listen a second time on a different day before finalizing. Fatigue-driven mishearing is real.
- If a segment matters legally (e.g., odor statement, consent exchange, dispensary statement), transcribe that segment a third time at reduced playback speed (0.75x) and note any discrepancy between passes rather than silently picking one.
- Every transcript file gets a header block: source filename, source hash, model version, date transcribed, transcriber name, confidence caveat.

---

## 5. Key Frame Extraction

```bash
ffmpeg -i ../originals/bodycam_01.mp4 -ss 00:02:14 -vframes 1 \
  ../derived/frame_odor_statement_022:14.jpg
```
- Name frames descriptively: `frame_[event]_[timestamp].jpg`, never `frame1.jpg`.
- Optional self-authentication overlay:
```bash
ffmpeg -i ../originals/bodycam_01.mp4 -vf "drawtext=text='%{pts\:hms}':x=10:y=10:fontsize=24:fontcolor=white" \
  -ss 00:02:14 -vframes 1 ../derived/frame_odor_statement_burned.jpg
```
- Extract BOTH a clean frame and a timestamp-burned frame for every key moment. Clean version for potential exhibit use; burned version for your own reference log.

---

## 6. Image Normalization (HEIC → JPG)

```bash
cd evidence/originals
for f in *.HEIC; do
  ffmpeg -i "$f" "../derived/$(basename "$f" .HEIC).jpg"
done
```
- Do this locally. Do not route images through third-party AI tools (e.g., ChatGPT) for format conversion — every additional service handling restricted recordings/photos is an additional disclosure risk and an additional link in the custody chain you'd have to account for.
- PNG, JPG, PDF all ingest natively into this system — no conversion needed for those.

---

## 7. The Event Log — The Actual Analyzable Artifact

This is the highest-value output. A transcript alone is hard to use; a structured log tied to your affidavit is not.

`logs/event_log.csv` columns:
`timestamp | speaker | action_or_statement | direct_quote | affidavit_paragraph_ref | confidence (high/med/low) | source_file`

Populate row by row while reviewing. Cross-reference every entry against `BEYLIN_AFFIDAVIT_26CR294791-170.md` paragraph numbers. Where the footage contradicts a paragraph, flag it in a `CONFLICT` column rather than silently editing the affidavit — conflicts must be resolved deliberately, not overwritten.

---

## 8. Priority Order (time-constrained: 9 days to hearing)

Process in this order, stop when time runs out:
1. The 90 seconds surrounding the first odor statement.
2. Opening 120 seconds of the stop (documents, initial questions).
3. Exit-order / handcuffing sequence — establish exact order of cuffing vs. search resumption.
4. Trunk-opening and every recovery event, with timestamps (currently highest priority given the cannabis-recovery correction).
5. Full remaining footage, lowest priority.

---

## 9. Upload Checklist — What This System Can Ingest

| Format | Ingestible? | Action |
|---|---|---|
| MP4/MOV raw video | No | Convert per steps 3–5 first |
| WAV/MP3 audio | No direct analysis | Transcribe per step 4 first |
| Transcript (.txt/.md) | Yes | Upload directly |
| Key frames (.jpg/.png) | Yes | Upload directly |
| Event log (.csv) | Yes | Upload directly |
| HEIC photos | No | Convert per step 6 |
| PDF/JPG/PNG documents | Yes | Upload directly, no conversion |

---

## 10. Final Pre-Upload Check

- [ ] Legal gate (§0) confirmed and logged
- [ ] Original hashes recorded, files read-only
- [ ] Manifest complete
- [ ] Transcript two-pass reviewed, `[INAUDIBLE]` used honestly
- [ ] Key frames named descriptively, timestamped
- [ ] Event log cross-referenced to affidavit paragraphs, conflicts flagged not resolved silently
- [ ] No derivative file shared, posted, or discussed outside this project/counsel/court

**v2 changes from v1:** added legal-gate confirmation log, weekly re-hash integrity check, two-pass + reduced-speed transcription for legally material segments, conflict-flagging rule instead of silent affidavit edits, explicit priority order for time constraint, and a header-block requirement on every transcript file for evidentiary traceability.

---

## APPENDIX: Instructions for Use in a File-Capable LLM/Agent

This skill was authored in an environment that cannot read video/audio files directly. To use it in an LLM or agent that CAN ingest video, audio, and images natively (e.g., a multimodal assistant with file upload, or a coding agent with a sandbox and ffmpeg/Whisper access), do the following:

1. **Upload this entire file** to the target system as a system/skill/instruction document, or paste its contents into the system prompt / custom instructions field.
2. **Tell the target LLM explicitly**: "Follow this SOP exactly, in order, section by section. Do not skip the legal gate in §0. Log every action to the files described in §1, §2, §7, and §10. Ask me to confirm before executing any step involving file conversion if you are unsure of the source or legal status of a recording."
3. If the target system has code execution / a sandbox with ffmpeg and Whisper (or equivalent) available, it can run the bash commands in §3–§6 directly. If not, ask it to describe equivalent steps using whatever tools it has (e.g., built-in transcription, built-in image conversion) while preserving the SAME rules: hash-first, read-only originals, two-pass transcription, conflict-flagging, provenance headers.
4. Feed it your evidence files (bodycam video, audio, HEIC photos) directly — the target LLM should perform §1 (hashing/manifest) BEFORE any conversion, and should output the manifest and derivation log for your review before proceeding further.
5. Review every output (transcript, event log, key frames) yourself. This skill instructs the LLM to flag uncertainty (`[INAUDIBLE]`, `CONFLICT`) rather than resolve it — you are the one who resolves it, using your own knowledge of what happened.
6. Once transcripts, key frames, and the CSV event log are produced and reviewed by you, THOSE files (not the raw video/audio) are what you upload back into this project (Perplexity), which can ingest text, CSV, PDF, JPG, and PNG natively.
7. Do not upload raw bodycam video or audio to any third-party LLM/service unless you have confirmed under §0 that doing so does not violate the terms of a § 132-1.4A release order or a § 15A-908 protective order. When in doubt, use a local tool (ffmpeg + local Whisper install, run entirely on your own machine) rather than a cloud LLM, so the recording never leaves your control.

END OF SKILL FILE.
