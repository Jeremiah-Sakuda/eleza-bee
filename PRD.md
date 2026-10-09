# Eleza (Bee) PRD v1.0

**Track:** Bee (Wearable AI), Education priority
**Mini challenge:** Open Source
**Deadline:** Oct 23, 2026, 3:00 PM EDT
**Status:** Draft for scope lock. Decisions D1 and D2 must close before any build session.
**Relationship to existing Eleza:** Eleza existed before the submission period as an instructor-side oral-defense evidence tool. This PRD defines the student-side surface built in the window. Section 13 states the significant update as the rules require.

---

## 1. One line

Eleza shows you what you can explain without the notes in front of you.

## 2. Problem and user

Students study by re-reading, which feels like learning and mostly isn't. Explaining the material out loud, unaided, is what works, and almost nobody does it because nothing tells them whether what they said was right. Meanwhile oral assessment is spreading (EC 427 at BU already grades coding assignments by interview), so the first time most students find out they can't explain something is in front of the person grading it.

**User:** one undergraduate in a lecture course who wears Bee (on Apple Watch) and explains this week's material out loud on a walk they were already taking. The demo course is BI 107. The user has no notes in hand; that is the point.

**What Eleza does:** captures the explanation through Bee, aligns each thing the student said to the passage in the course text it came from, and reports what was covered, what was skipped, and where the explanation contradicted the text, each line tied to the sentence the student said and the passage it maps to. The next day, the wrist prompts the gap. Over weeks, a ledger shows which concepts hold without notes and which keep slipping.

**What Eleza is not:** a tutor. It never explains the material back, never quizzes, never scores. It shows the student the distance between what they said and what the text says, and the student closes it.

## 3. Non-goals (v1)

- Dialogue, explanations, hints, or Socratic questioning. The only outbound prompt is the next-day gap prompt (ELZ-500).
- Scores, grades, mastery labels, streaks, or gamification
- Flashcards, quizzes, or spaced-repetition scheduling beyond the gap prompt
- Instructor dashboard or sharing with an instructor. One sentence of future direction in the pitch connects this to Eleza's instructor side; nothing built.
- Aligning against the professor's own slides or recordings (rights; see ELZ-201)
- Pronunciation, fluency, or delivery feedback (Bee exposes text, not audio features)
- Multi-device orchestration (Bee + Echo + Fire TV). One sentence of future direction, nothing built.
- Letting other users connect their Bee (not required by the rules)

## 4. Invariants

Named, numbered, and quoted in AGENTS.md as prohibitions.

- **INV-1 Wearer only.** Only the wearer's own utterances are stored, aligned, or shown. Any other speaker captured during a session (a passerby, a friend who says hi) is discarded at the end of the session window and never persisted, logged, or displayed.
- **INV-2 Source-bound.** Every "covered," "skipped," and "contradicted" line cites exactly one passage ID in the course source and, for covered and contradicted, exactly one utterance ID from the session. No line may assert anything about the material that is not in the cited passage.
- **INV-3 Evidence, not verdict.** The report shows the student's words next to the text's words and stops. No score, no percentage, no "mastered." A concept that stops appearing in the skipped list is reported as "not skipped since <date>." The student can mark any line **I said it differently**; marked lines are excluded from the ledger.
- **INV-4 Deterministic first.** Claim segmentation and candidate-passage retrieval are rule- and retrieval-based with tested thresholds. A language model may label a (claim, passage) pair as supports / contradicts / unrelated and may write the one-line gap prompt. It may not originate a claim the transcript does not contain, a passage the source does not contain, or a pair the retriever did not propose.
- **INV-5 Never interrupt.** Nothing is delivered while a session is open. The report arrives after the session closes.
- **INV-6 No fabricated data.** Every session in the demo and every number in FINDINGS.md comes from the real wearer, the real device, and real walks during the window. Detector and aligner numbers are measured on hand-labeled fixtures and reported without targets set in advance.
- **INV-7 No authoring-tool attribution.** No mention of any AI assistant or authoring tool anywhere in the repo, commits, docs, or video.

## 5. Requirements

### Capture (ELZ-100)

- **ELZ-101** Bee runs on the wearer's Apple Watch with Developer Mode enabled in the Bee app. The CLI is authenticated on the build machine.
  *AC:* `bee stream --json --types new-utterance` prints live utterances from a real walk, and `bee sync --only conversations` exports the same session with speaker labels. Both captured to BUILD-LOG.md on day one.
- **ELZ-102** The runtime hook is in code: the Eleza session service subscribes to the Bee stream (or polls the sync feed) at startup. This is an import and an entry point, not a README mention (rules requirement for Bee).
- **ELZ-103** Session boundaries, per D1. Default: a spoken start marker ("Eleza, glycolysis") opens a session and names the unit; a spoken stop marker ("Eleza, done") or four minutes of silence closes it. The markers are matched by rule over the stream. If Bee's Voice Notes are reachable through the CLI, D1 may switch capture to Voice Notes; the rest of the pipeline is unchanged.
- **ELZ-104** Wearer identification. A one-time calibration maps Bee's speaker label to the wearer. If labels arrive as `Unknown` on a solo walk, the session is treated as wearer-only after the fact and the case is logged as friction.
  *AC:* Documented in README; the `Unknown` rate is a friction log entry with severity and workaround.
- **ELZ-105** Term normalization. Before alignment, transcribed tokens are fuzzy-matched against the unit's glossary (built from the source's bolded terms and headings) so that "phospho fructo kinase" becomes `phosphofructokinase`. Normalizations are logged per session and reported in FINDINGS.md as the transcription correction rate. This is engineering, not prompting (INV-4).

### Source (ELZ-200)

- **ELZ-201** The aligned source is an open textbook, not the professor's materials. Default: OpenStax Biology 2e (CC BY 4.0), the chapters matching BI 107's current units. The license and attribution appear in the README and the app.
- **ELZ-202** Ingestion uses Docling to parse the textbook PDF into sections and paragraphs with stable passage IDs, headings, and bolded terms. The parse is committed as data so the demo does not depend on re-running it.
- **ELZ-203** A unit is a named set of passage IDs (for example, "Glycolysis" = section 7.2 paragraphs 1–9). Units are defined in a small YAML course map the student edits once per week. The demo ships the map for the BI 107 weeks inside the window.
- **ELZ-204** Each unit carries a list of key ideas: one per passage by default, editable. "Skipped" is computed against key ideas, so the report says "you skipped the role of NAD+" rather than "you skipped paragraph 6."

### Alignment (ELZ-300), the open-source library

- **ELZ-301** Claim segmentation: the session transcript is split into claims at sentence boundaries, with discourse fragments ("um," "okay so," false starts) dropped by rule. Each claim keeps its utterance ID and timestamp.
- **ELZ-302** Candidate retrieval: for each claim, the top-k passages in the unit by a hybrid lexical plus embedding score, with a threshold below which the claim is "unaligned" and never sent to the labeler.
- **ELZ-303** Pair labeling: a language model labels each (claim, candidate passage) pair as **supports**, **contradicts**, or **unrelated**, and for supports and contradicts returns the single sentence in the passage the claim maps to. Output is structured; any response that cites text not present in the passage is rejected by a string check (INV-2).
- **ELZ-304** Coverage: a key idea is **covered** if at least one claim supports its passage, **contradicted** if at least one claim contradicts it, **skipped** otherwise. A key idea can be both covered and contradicted; the report shows both.
- **ELZ-305** The library (`eleza-align`) is standalone, MIT, with unit tests over hand-labeled fixtures: at least ten real session transcripts with claims labeled by the wearer. Segmentation precision, retrieval hit rate at k, and labeler agreement with the wearer's labels are reported in FINDINGS.md. No target is set in advance.
- **ELZ-306** The library knows nothing about Bee or biology. Input is a transcript with utterance IDs and a passage set with IDs; output is the coverage structure. This is what makes it a useful primitive for anyone building on conversational wearables or oral assessment.

### Report (ELZ-400)

- **ELZ-401** Report format, fixed:
  **Covered** (count, then key ideas) / **Skipped** (key ideas) / **Contradicted** (for each: *You said* [claim] / *The text says* [sentence] / passage link).
  No praise, no scoring language, no suggestions beyond the gap prompt.
- **ELZ-402** Each line is tappable to its utterance and its passage, side by side (INV-2, INV-3).
- **ELZ-403** Delivery: after session close, one notification ("Glycolysis: 7 of 11 ideas, 1 contradiction"). The student opens it when they choose (INV-5).
- **ELZ-404** Each contradiction and each skipped idea has two actions: **Got it** and **I said it differently** (exclude from ledger).

### Gap prompt (ELZ-500)

- **ELZ-501** The next day, one prompt on the wrist, built from the ledger: the most recently skipped or contradicted key idea for the current unit, phrased as the idea's name only ("Yesterday you skipped the role of NAD+. Try it on today's walk."). The prompt never includes the explanation.
- **ELZ-502** Prompt time is set by the student. Optional: Bee's facts and daily summary, read through the MCP server, suggest a time when the student usually walks. Read-only; nothing is written back to Bee. Ship only if it costs under half a day.
- **ELZ-503** An Agent Skill (`eleza-session`) packages the loop for a coding agent or power user: pull the latest session from Bee MCP, run `eleza-align` against the unit, write the report. This is the reproducibility path for judges and the rubric's "Agent Skills for on-wrist coaching" item.

### Ledger (ELZ-600)

- **ELZ-601** An append-only ledger of sessions, coverage results, and student actions. Nothing is edited in place.
- **ELZ-602** Weekly insight, written as counts and examples, never as a score: "This week: 5 sessions. Covered without prompting: 14 ideas. Still skipping: NAD+ regeneration (3 sessions). Contradicted twice: where ATP is invested." Each line links to its sessions.
- **ELZ-603** Recurrence is the signal. A key idea that was skipped and is then covered in two consecutive sessions is reported as "not skipped since <date>."

### Delivery surface (ELZ-700)

- **ELZ-701** Decision D3 governs. If watchOS: a minimal companion app (iOS host + watchOS target) showing the notification summary, the gap prompt, and the two actions on the wrist, with the full report on the phone. If notifications: iPhone rich notifications with the summary and actions, full report in a simple phone view.
- **ELZ-702** Whichever surface ships, the demo must show a report arriving after a real walk on the actual watch or phone, not a mock.

### Open Source mini (ELZ-800)

- **ELZ-801** `eleza-align` ships as its own public repo, MIT licensed, created during the submission window, with tests, fixtures (the wearer's own, with consent noted), and a README explaining claim-to-passage alignment as a primitive for oral assessment and wearable learning.
- **ELZ-802** Submission fields: contribution URL, main repo URL, GitHub username, and a description of what it does, how it works, why it matters.

### Documentation (ELZ-900, non-negotiable)

- **ELZ-901** README with setup, run, calibration, and course-map instructions; architecture diagram; FINDINGS.md (segmentation precision, retrieval hit rate, labeler agreement, transcription correction rate, sessions per week, ledger observations, all measured); BUILD-LOG.md; friction log with one entry per real friction (task, steps, expected, actual, severity, workaround, suggestion).
- **ELZ-902** Product feedback answer covers Bee CLI, stream, sync, MCP, and Agent Skill separately: what each was used for, what worked, what needs work, onboarding, would build again.
- **ELZ-903** A "What changed since Aug 31" section in the README with the baseline tag and a compare link (Section 13).

## 6. Architecture (plain language)

```
Apple Watch running Bee
      │  (Bee processes audio, produces transcript)
      ▼
bee stream / bee sync  ──►  Eleza session service
                                 │
                                 ├─ session markers: open / close by rule (ELZ-103)
                                 ├─ term normalization against unit glossary (ELZ-105)
                                 ├─ eleza-align (open source):
                                 │     segment claims → retrieve passages → label pairs → coverage
                                 ├─ report builder: fixed format, every line cites spans
                                 ├─ ledger: append-only sessions, results, actions
                                 └─ Bee MCP (read-only, optional): walk-time suggestion
                                 │
                                 ▼
                     Report after session close (watchOS card or iPhone notification, per D3)
                     Gap prompt next day on the wrist

Course source: OpenStax Biology 2e ──► Docling parse ──► passages + glossary + course map
```

The LLM provider is a build decision. Bedrock is acceptable but not required (Open Source is the mini); do not add AWS for its own sake.

## 7. Demo (under 3 minutes)

The video is scored on the same four criteria as the project. Lead with the moment of finding out.

1. **0:00–0:20** A walk, no notes. The student explaining glycolysis out loud, mid-sentence. Title: *Eleza. Say it without the notes.*
2. **0:20–0:35** Still walking, still talking. Nothing on the wrist. Caption: *Eleza never interrupts.*
3. **0:35–0:50** The session ends. The wrist: "Glycolysis: 7 of 11 ideas. 1 contradiction."
4. **0:50–1:20** The phone. The contradiction, both spans side by side: *You said* ATP is produced in the first phase. *The text says* the first phase consumes two ATP. Then the skipped list. Caption: *Your words next to the text's words. No score.*
5. **1:20–1:50** Engineering, visible and labeled: Bee stream event → claim segments → candidate passages with scores → label → report line. Thirty seconds, no code dumps.
6. **1:50–2:15** Next morning. The wrist: "Yesterday you skipped the role of NAD+. Try it on today's walk." The walk. That evening's report: covered.
7. **2:15–2:35** One week later: the weekly insight. Counts, not scores. "Not skipped since Oct 17."
8. **2:35–2:50** Privacy and source in one line each: only your words are kept; the textbook is open. The `eleza-align` repo on screen.
9. **2:50–3:00** One sentence of future direction: the same engine already serves instructors running oral assessments.

## 8. Judging map

| Criterion | What earns it |
|---|---|
| Tech Implementation | Live stream + sync + MCP read + Agent Skill, all called at runtime; Docling source ingestion; tested alignment library with measured numbers; term normalization as engineering |
| Design | Ambient capture, zero effort beyond the walk, never interrupts, fixed report format, two actions, one prompt per day |
| Potential Impact | One specific user with a weekly recurring problem; every student in a lecture course; oral assessment is spreading, so the stakes are rising |
| Quality of the Idea | Matches the rubric's own examples (on-wrist coaching via Agent Skills, self-improvement workflow, facts and insights) while being a real product with an existing engine behind it |

## 9. Decisions to close before building

- **D1 Session boundary.** Spoken start/stop markers vs Bee Voice Notes vs a solo-speaker heuristic. Test which the CLI exposes cleanly. Close by Oct 11. Default if unresolved: spoken markers over the stream.
- **D2 Transcription of technical vocabulary.** One real walk explaining this week's BI 107 unit, captured through `bee stream`. Measure how many unit glossary terms survive transcription before and after term normalization. Close by Oct 10, in the first build hour, before any other work. Whatever the number, it goes in FINDINGS.md and the friction log.
- **D3 Delivery surface.** watchOS companion app vs iPhone notifications. Close by Oct 13. Default if unresolved: iPhone notifications (protects the demo).
- **D4 Course map.** Which BI 107 units fall inside the window and which OpenStax sections they map to. Close by Oct 11.
- **D5 Repo visibility.** Main Eleza repo: public with license, or private and shared with testing@devpost.com and the listed Amazon GitHub users. Default: private and shared (protects the instructor-side product), with `eleza-align` public.

## 10. Kill switches

- **K1** If after term normalization the retriever cannot find the right passage for most claims in the D2 walk, the demo moves to a vocabulary-light unit for one more test. If that also fails, the entry is cut and the effort moves to Sema.
- **K2** If `bee stream` does not deliver usable utterances by Oct 12, switch to sync-only (post-hoc) processing and drop "real-time" from all claims.
- **K3** If no session boundary mechanism works through the CLI, the phone app gets a manual Start/Stop and the friction is logged.
- **K4** If fewer than five real sessions exist by Oct 20, the weekly insight beat is cut from the video rather than shown on thin data.

## 11. Risks

| Risk | Mitigation |
|---|---|
| Judges file it under AI tutoring (ReExplain, Feynman AI, any chatbot) | No dialogue, no explanations, no score. The pitch names the prior art and separates on form (unaided, on a walk) and on the longitudinal record |
| Bee natively summarizes lectures | The demo shows the contradiction with both spans, which a summary cannot produce |
| Transcription mangles enzyme names | D2 first hour; term normalization; honest correction rate in FINDINGS.md; K1 |
| Source rights | Open textbook, CC BY, attributed; professor's materials never ingested |
| "Existing project" rule | Baseline tag, compare link, Section 13 explanation; Bee integration, student surface, open-source library, ledger, and prompts are all in-window |
| Labeler marks a correct paraphrase as a contradiction | The student's **I said it differently** action excludes it; disagreement rate reported |
| watchOS app eats the schedule | D3 default protects the demo; the watch surface is upside, not the core |

## 12. Deliverables checklist

- [ ] Main Eleza repo (per D5: public with MIT visible in About, or private and shared with testers and the Amazon team)
- [ ] `eleza-align` repo (public, MIT, created in-window, tests and fixtures)
- [ ] README with "What changed since Aug 31," architecture diagram, FINDINGS.md, BUILD-LOG.md, friction log
- [ ] Demo video (YouTube/Vimeo, public, English, under 3:00, no third-party marks or music) showing a report arriving after a real walk
- [ ] Product feedback per tool
- [ ] Open Source mini fields
- [ ] OpenStax attribution in README and app

## 13. Significant update statement (rules requirement)

Before Aug 31, 2026, Eleza was an instructor-side web tool: upload a recorded oral defense, receive a dossier linking the student's claims to transcript spans, no verdicts. Everything in this PRD is new in the submission window: Bee capture on Apple Watch with session markers and term normalization; open-textbook source ingestion with a course map; the alignment engine extracted into `eleza-align` and open-sourced with tests; the student-side report, the next-day gap prompt, and the append-only ledger; the Agent Skill. The commit at the start of the window is tagged `pre-hackathon`; the README links a compare view against it, so the git history proves what was built when.