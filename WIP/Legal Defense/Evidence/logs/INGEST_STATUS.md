# INGEST_STATUS — 26CR294791-170
Date: 2026-08-13
Operator: ib-mac
Custody: `WIP/Legal Defense/Evidence`
Source: `/Users/ib-mac/BODYCAM,PHOTOS` (read-only; not chmod'd)
Classification: investigation artifacts. **Not court-ready.** Not legal advice.

## Result legend
Passed / Failed / Skipped / Unknown — every applicable gate below.

## Scope executed
- Legal gate logged. Local-only. Protective order: **Unknown**.
- 53 media files copied/hashed (plan said 50; folder actually has 4 MP4 + 48 Axon JPG + 1 `IMG_7261_2.jpeg`).
- Skill §8 / protocol §6: **priority windows only**. Full remaining footage not processed.
- `0153` pass-1 draft harvested from mlx-whisper stdout already covering the action (file-elapsed ~00:00:36–00:08:48). File was **not cropped**; timestamps are original elapsed time.
- `0211` / `0312` / `0426`: WAV extracted; ASR **Skipped** (remainder / other-camera full length). Recovery stills indexed instead of transcribing hours of idle video.
- Homebrew ffmpeg 9.0.1 has **no drawtext filter**. Burned frames stamped with Pillow using the **file-elapsed seek time** (not decoder PTS, which would read 00:00:00 after `-ss`).

## Acceptance gates

| Gate | Result | Evidence |
|---|---|---|
| Source folder hash-identical to preflight listing | Passed | `logs/source_hashes_precopy.txt` vs `logs/original_hashes_20260813_112753.txt` (SHA-256 values identical; 53 files). Earlier `112533` log had a filename-split bug from the space in `Legal Defense`; hashes still matched. |
| 50 files in originals/; hash diff empty; copies mode 444 | Passed with count note | **53** files in `originals/` (not 50). Copies mode `444`. Source folder left untouched (still writable). |
| Manifest 50 present + 1 ABSENT dashcam; `date_received=Unknown` | Passed with count note | `logs/evidence_manifest.csv`: **53 present + 1 ABSENT** `DASHCAM_OR_FIFTH_VIDEO`. All `date_received=Unknown`. |
| Each MP4 has WAV whose derivation log cites that file’s SHA-256 | Passed | Four `working/*_audio.wav` rows in `logs/derivation_log.csv`. |
| Each processed MP4 has header-blocked draft transcript (json + txt) | Passed (0153 only) / Skipped (0211, 0312, 0426) | `derived/transcripts/Axon_Body_4_Video_2026-04-30_0153_D01AQ340U.{json,txt,tsv}` header includes source filename, SHA-256, model, date, operator, `DRAFT — not court-ready`. Other three MP4s: skill §8 item 5/6 remainder; not run. |
| Priority frames for odor window, or Unknown with search evidence | Passed | 24 frames (12 clean + 12 burned) under `derived/frames/`, including `T00-01-54_marijuana_question_*` and `T00-01-58_odor_statement_*` from **this file’s** draft (elapsed 00:01:54 / 00:01:58). Direct media matched SRC013 search hint; overlay not rewritten. |
| Event log zero protocol-sample seed rows; Whisper quotes `WHISPER_DRAFT` | Passed | `logs/EVENT_LOG_20260430.csv`: 70 rows this batch only. 21 `WHISPER_DRAFT` (confidence `low`, never `high`). 49 `STILL_VISUAL`. 4 `CONFLICT` (F004, F005 sequence; F011 plant/mushroom-like stills). Overlay/affidavit not edited. |
| `Evidence/.gitignore` (`*` / `!.gitignore`); originals MP4 ignored; tree not staged | Passed | `git check-ignore` on an `originals/` MP4 and on the 0153 transcript: ignored. Nothing from this tree staged. Nested gitignore required because `WIP/` is tracked. |
| No cloud STT in command log | Passed | mlx-whisper local `large-v3` only. HF used for **weights** then `HF_HUB_OFFLINE=1`. No OpenAI Whisper API / ChatGPT / HF Spaces for media. |
| No files under `~/Legal-Defense/` | Passed | Path unused. |

## What the 0153 draft actually shows (pass-1, not court-ready)
File-elapsed clock on `Axon_Body_4_Video_2026-04-30_0153_D01AQ340U.mp4`:

- ~00:01:22 contact (“How you doing, sir?”)
- ~00:01:34 improper-turn reason
- ~00:01:54 “Do you smoke marijuana?”
- ~00:01:58–00:02:01 odor (“I can smell something” / “smells a whole lot like marijuana”)
- ~00:02:20 drinking question (after odor)
- ~00:02:43 firearm in vehicle
- ~00:03:04–00:03:10 exit order after odor + partner arrival
- ~00:03:17 search announced as PC of marijuana / possible impairment
- ~00:05:06–00:05:13 search for marijuana; driver “a little bit of marijuana”
- ~00:05:30 CBD-shop question (after odor — **CONFLICT vs overlay F005**)
- Coverage ends ~00:08:48. Gap ~00:06:07–00:08:46. No trunk-opening speech in this harvested window.

**CONFLICT (logged, overlay not edited):** F005 dispensary-before-odor; F004 drink-then-cannabis order. F011 vs stills of plant/mushroom-like material.

## Explicit skips / unknowns
- Protective order text (§ 15A-908): **Unknown**
- True DA receipt date: **Unknown** (mtime is not receipt)
- Officer-to-device mapping: **Unknown** until visual confirmation (not assigned in manifest)
- Dashcam / 5th video: **ABSENT** this batch
- `0211` `0312` `0426` ASR: **Skipped** (skill §8 remainder)
- Trunk-opening **on video** (item 4 of protocol): **Unknown** this pass — not in the 0153 action window already transcribed. Recovery **stills** 07:06–07:48 are indexed in `stills_index.csv` / event log (`filename_clock`, not a unified master clock).
- Human second-listen / 0.75x: operator-owned
- Compiled corpus rewrite: not done
- Court-ready claim: **not made**

## Hard stops encountered
None of: protective order forbidding copies; hash mismatch; unreadable MP4; disk < 5 GB; media upload off-box.

First full-file Whisper run looped on “Okay” (~04:08) with `condition_on_previous_text=True`. Killed. Second run used clip-timestamps on the **full** WAV (no crop). Stopped after the action window per operator.

## Operator next
Second listen on odor / consent / recovery lines; 0.75x on legally material segments; locate trunk-opening on whichever file actually contains it using file-elapsed seek (do not crop from 00:00); later corpus promotion.
