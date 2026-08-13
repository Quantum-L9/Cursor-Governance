# EVIDENCE INGESTION PROTOCOL
## Bodycam, Dashcam, and Photographs → AI-Analyzable Artifacts
## 26CR294791-170 | Issued 8/12/2026 | T-9 days to hearing

**DRAFT — PRO SE WORKING DOCUMENT.** Not legal advice. Verify any protective order or release conditions before transmitting recordings to any third-party service.

---

# 0 — THE HARD CONSTRAINT

**Video and audio files cannot be analyzed here.** Uploading an MP4, MOV, MKV, WAV, or MP3 to Project Files produces nothing usable. There is no frame-by-frame viewing, no audio listening, no automatic transcription.

What **is** analyzable:

| Format | Analyzable | Notes |
|---|---|---|
| `.md`, `.txt` | Yes | Best format for transcripts and logs |
| `.pdf` | Yes | Text-layer PDFs read cleanly; scanned PDFs are weaker |
| `.png`, `.jpg`/`.jpeg` | Yes | Extracted video frames, photographs, screenshots |
| `.csv` | Yes | Timestamp logs, evidence indexes |
| `.docx` | Partially | Convert to PDF or Markdown for reliability |
| `.mp4`, `.mov`, `.mkv`, `.avi` | **No** | Must be converted |
| `.wav`, `.mp3`, `.m4a` | **No** | Must be transcribed |
| `.heic` | **No** | Convert to JPG |

**On the ChatGPT question: no, you do not need it, and you should not route evidence through an extra service for format conversion.** Every conversion below runs locally with ffmpeg and Whisper. Fewer copies in fewer places is better for both integrity and confidentiality.

---

# 1 — EVIDENCE INTEGRITY FIRST (DO THIS BEFORE ANYTHING ELSE)

Never process an original. Hash it, copy it, work on the copy.

```bash
mkdir -p ~/beylin/00_ORIGINALS ~/beylin/01_WORKING ~/beylin/02_DERIVED

# Move originals in, then lock them read-only
chmod 444 ~/beylin/00_ORIGINALS/*

# Hash every original — this is your authentication baseline
cd ~/beylin/00_ORIGINALS
shasum -a 256 * | tee ~/beylin/HASH_MANIFEST_$(date +%Y%m%d).txt

# Work only on copies
cp ~/beylin/00_ORIGINALS/* ~/beylin/01_WORKING/
```

Record for each file: original filename, source (who gave it to you and when), file size, SHA-256, duration, and device/camera if known. A derived transcript or frame grab is only as useful as your ability to show the court it came from an unaltered original.

**Preserve original file metadata.** Do not re-encode, trim, rotate, or "clean up" any original. All manipulation happens on copies in `01_WORKING`, and every derived product lands in `02_DERIVED`.

---

# 2 — AUDIO → TRANSCRIPT (HIGHEST VALUE, DO THIS FIRST)

The transcript is worth more than the video for hearing prep. It is searchable, quotable, and directly usable in cross-examination.

```bash
cd ~/beylin/01_WORKING

# Extract audio at 16 kHz mono — optimal for speech recognition
ffmpeg -i bodycam_mcmurtry.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le audio_mcmurtry.wav

# Transcribe with word-level timestamps
whisper audio_mcmurtry.wav \
  --model large-v3 \
  --language en \
  --word_timestamps True \
  --output_format all \
  --output_dir ~/beylin/02_DERIVED/transcripts
```

This yields `.txt`, `.srt`, `.vtt`, `.tsv`, and `.json`. **Upload the `.txt` and the `.tsv`** — the TSV gives clean start/end timestamps per segment.

Then do a manual correction pass. Whisper mangles proper nouns, radio traffic, and overlapping speech. Correct against your own listening and mark every uncertain passage `[INAUDIBLE]` or `[UNCERTAIN: ...]`. **Never guess at a word in a document you may rely on in court.** A transcript with honest gaps is credible; a transcript with invented words is impeachable.

---

# 3 — VIDEO → FRAMES

## Targeted extraction (preferred)

Pull frames only at moments that matter. Cheaper, cleaner, and it forces you to identify the moments.

```bash
# Single frame at a precise timestamp — repeat per moment
ffmpeg -ss 00:04:12.500 -i bodycam_mcmurtry.mp4 -frames:v 1 -q:v 2 \
  ~/beylin/02_DERIVED/frames/T00-04-12_odor_statement.png
```

Name every frame with its timestamp and what it shows. That filename becomes your exhibit label.

## Systematic extraction (for a segment you need to study)

```bash
# One frame per second across a specific window
ffmpeg -ss 00:03:00 -to 00:06:00 -i bodycam_mcmurtry.mp4 \
  -vf fps=1 -q:v 2 ~/beylin/02_DERIVED/frames/seg03-06_%04d.png
```

Keep uploads to a few dozen frames maximum. A thousand frames of a dark rural roadside is noise.

## Burn timestamps into the frames

```bash
ffmpeg -i bodycam_mcmurtry.mp4 -vf \
  "drawtext=text='%{pts\\:hms}':x=10:y=10:fontsize=28:fontcolor=yellow:box=1:boxcolor=black@0.6,fps=1" \
  -q:v 2 ~/beylin/02_DERIVED/frames/stamped_%04d.png
```

Visible timestamps make a frame self-authenticating in a way a bare image is not.

---

# 4 — PHOTOGRAPHS

```bash
# HEIC → JPG (iPhone photos)
for f in *.HEIC; do ffmpeg -i "$f" -q:v 2 "${f%.HEIC}.jpg"; done

# Downscale anything enormous, preserving legibility
mogrify -path ~/beylin/02_DERIVED/photos -resize 2400x2400\> -quality 90 *.jpg
```

Rules: export originals rather than screenshotting them; keep EXIF intact on originals; do not crop, rotate, enhance, or annotate the copies you upload — annotate in a separate document that references the filename.

---

# 5 — THE FRAME-BY-FRAME LOG (THE MOST USEFUL SINGLE ARTIFACT)

Neither a transcript nor a frame set captures what you saw. Write the log yourself, in CSV, watching the video with a timestamp readout.

```csv
timestamp,source,actor,type,content,significance
00:00:00,bodycam_mcm,SYSTEM,event,Recording begins,Pre-stop baseline
00:00:47,bodycam_mcm,MCMURTRY,event,Emergency equipment activated,Seizure begins
00:01:12,bodycam_mcm,BEYLIN,event,Vehicle stopped fully,No evasion — Aff. para 6
00:01:38,bodycam_mcm,BEYLIN,speech,"I have a concealed handgun permit",UNPROMPTED — Glover subtraction — Aff. para 8
00:01:55,bodycam_mcm,MCMURTRY,speech,"Reason I stopped you is the turn back there",Stop basis stated — Aff. para 9
00:02:20,bodycam_mcm,BEYLIN,event,License/registration/insurance produced,Prompt — Aff. para 10
00:03:05,bodycam_mcm,MCMURTRY,speech,"Have you had anything to drink tonight?",OFF-MISSION #1 — Aff. para 11
00:03:30,bodycam_mcm,MCMURTRY,speech,"Where are you headed?",OFF-MISSION #2 — Aff. para 13
00:03:52,bodycam_mcm,MCMURTRY,speech,"Was that from a dispensary?",OFF-MISSION #3 — Aff. para 14
00:04:12,bodycam_mcm,MCMURTRY,speech,"I smell marijuana",ODOR CLAIM — FIRST MENTION — Aff. para 15
00:05:40,bodycam_mcm,MCMURTRY,speech,"I have probable cause to search the vehicle",Aff. para 18
00:05:48,bodycam_mcm,BEYLIN,speech,"You don't have to do this",Aff. para 19
00:05:51,bodycam_mcm,MCMURTRY,speech,"I'm going to conduct my investigation",Aff. para 19
```

Continue through: exit order, search start, trunk opening, each item recovered with timestamp, handcuffing, resumption of search, placement in patrol unit, end of recording.

**Timestamps are the whole point.** The elapsed time between the stated stop mission and the odor claim is the *Rodriguez* prolongation measurement, and the ordering of the dispensary question versus the odor claim is the entire *Dobson* subtraction argument.

---

# 6 — WHAT TO EXTRACT FIRST, GIVEN NINE DAYS

Do not process the entire event before the hearing. Prioritize in this order:

1. **The 90 seconds surrounding the first odor statement.** Transcript plus frames. This is Block D of the cross and the core of the closing argument.
2. **The first 120 seconds of the encounter.** Confirms the unprompted permit disclosure and prompt document production.
3. **The exit-order and pre-search exchange.** Confirms or refutes the exact words at Aff. ¶¶18–21.
4. **Trunk opening and every recovery event, with timestamps.** This is now mandatory following the 8/12 cannabis correction. You need to know precisely what the video shows recovered, from where, and when — before you ask any officer any question about recovery.
5. **Handcuffing versus search resumption.** Aff. ¶¶24–26.
6. Everything else.

Item 4 is non-negotiable. The cross script cannot be rebuilt until you have watched the recovery sequence and reported exactly what it shows.

---

# 7 — WHAT TO UPLOAD TO PROJECT FILES

| Artifact | Format | Filename convention |
|---|---|---|
| Corrected transcript per recording | `.md` | `TRANSCRIPT_bodycam_mcmurtry_CORRECTED.md` |
| Whisper timestamp table | `.tsv` or `.csv` | `TIMESTAMPS_bodycam_mcmurtry.tsv` |
| Frame-by-frame log | `.csv` | `EVENT_LOG_20260430.csv` |
| Key frames | `.png` | `T00-04-12_odor_statement.png` |
| Photographs | `.jpg` | `PHOTO_trunk_case_01.jpg` |
| Hash manifest | `.txt` | `HASH_MANIFEST_20260812.txt` |
| Evidence index | `.csv` | `EVIDENCE_INDEX.csv` |

Redact before upload: your DOB, driver's license number, SSN if visible anywhere, and any third party's face or identifying information not relevant to the stop.

---

# 8 — LEGAL CAUTION ON DISSEMINATION

North Carolina treats law enforcement recordings under a restrictive two-tier regime. **Disclosure** means you may view but not copy. **Release** means you receive a copy, and recordings in an agency's custody may be released **only pursuant to court order**. A court ordering release "may place any conditions or restrictions on the release of the recording that the court, in its discretion, deems appropriate."

Two points that matter for you:

1. **How did you get it?** If the recording came through a § 132-1.4A petition, read the order and comply with every condition on it before transmitting the file anywhere. Your project already contains a § 132-1.4A petition template, which suggests that route was contemplated. If it came through criminal discovery, the mechanism the State would use to restrict your handling is a protective order under § 15A-908 — check whether one exists.
2. **Once a copy is lawfully in your hands, § 132-1.4A's release restrictions govern recordings "in the custody of a law enforcement agency," not recordings in the custody of a defendant.** That distinction is favorable to you but it is not permission to publish. Do not post any frame, clip, or transcript publicly, do not share it with anyone outside this matter, and do not discuss its contents online. The standing no-public-statement rule covers derivative material.

Verify both points before the first upload.

---

# 9 — THE REASON THIS MATTERS MORE THAN IT DID THIS MORNING

The cannabis correction at 5:53 p.m. today established that the fact base for this hearing was built partly on inference rather than documents. You now hold the recordings that resolve the inference.

**Process the recovery sequence, report exactly what it shows, and the cross script gets rebuilt on documented fact instead of recollection.** That is the difference between a cross-examination that survives contact with a sworn officer and one that hands him the case.

---

**NEXT_ACTION:** Hash and copy all originals tonight, then produce the corrected transcript and timestamp log for (a) the 90 seconds around the first odor statement and (b) the full trunk-opening and recovery sequence, and upload both to Project Files by **Thursday, August 13, 2026**; owner: Beylin, pro se.

**DRAFT — PRO SE WORKING DOCUMENT. Not legal advice.**
