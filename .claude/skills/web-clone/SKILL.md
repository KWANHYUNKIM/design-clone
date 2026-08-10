---
name: web-clone
description: Clone a website's design pixel-for-pixel from a URL alone. Creates a per-project workspace, then orchestrates recon / architect / builder / verifier agents that drive Chrome to capture screenshots, extract real computed CSS (fonts, colors, spacing, grid), map the structure, build a self-contained index.html, and iterate clone-vs-original until they match. Trigger whenever the user supplies a URL and wants it recreated, copied, cloned, or rebuilt — even if they say nothing else.
---

# Web Clone — URL to pixel-identical HTML

The user gives **only a URL**. Everything else is yours: workspace, recon, screenshots, structure, build, verification. Never ask the user to take a screenshot or read a value off the page — you have Chrome.

You are the orchestrator. You do not do the capture or the typing yourself; you delegate to the four agents below and own the plan, the checkpoint, and the final report.

Write files and internal notes in English. **Report to the user in Korean.**

## The agents

| Agent | Does | Parallelism |
|---|---|---|
| `clone-recon` | Drives Chrome: screenshots, computed-CSS extraction, content, routes | One per URL×viewport — parallel, each in its own tab |
| `clone-architect` | Reads capture → `STRUCTURE.md`, `SECTIONS.md`, `TOKENS.css` | One per project, sequential |
| `clone-builder` | Writes one section as an HTML fragment + scoped CSS | One per section — parallel, each owns one file |
| `clone-verifier` | Screenshots the clone, diffs it against the original, reports defects | One per viewport or scroll band — parallel |

Parallelism is safe because each agent owns disjoint files and its own browser tab. It stops being safe the moment two agents write the same file — so builders write fragments and **you** assemble `index.html`.

## Ground rules

- **Measure, never eyeball.** A screenshot shows what it looks like; `getComputedStyle` says what it *is*. Guessing `#333` where the site uses `rgb(51, 51, 54)` is the single biggest source of "almost, but not quite".
- **One self-contained output**: `04-build/index.html`, inline `<style>`, no build step, no CDN. Assets in `04-build/assets/`.
- **Never invent content.** Real text, real hrefs, real images from the extraction. Lorem ipsum defeats the point.
- **Batch browser calls** with `browser_batch` — one call per scroll is slow.
- **Read-only browsing.** No sign-ups, purchases, or form submits. Cookie banners: choose the privacy-preserving option and say what was clicked. **Never solve a CAPTCHA.**
- **Attribution.** This is a study reproduction. If the user wants to publish it, tell them to replace the brand name, logo, and copy first.

## Phase 0 — Project workspace

Every URL gets its own folder. Slug it from the domain plus page (`stripe-com-pricing`), and if that folder exists, suffix `-2`, `-3` — never overwrite a previous run.

```
projects/<slug>/
  01-reference/     original screenshots (desktop-01.png, mobile-01.png, *-detail-*, *-hover-*)
  02-extract/       raw computed CSS + content pulled from the live page — the evidence layer
  03-structure/     STRUCTURE.md, SECTIONS.md, TOKENS.css — the plan
  04-build/         index.html, sections/, assets/
  05-verify/        clone screenshots + defect reports per round
  NOTES.md          running log: URL, date, decisions, substitutions, blockers
```

Create all six, then start `NOTES.md` with the URL, the date, and the user's stated scope. Every phase appends to it — it is what makes a run resumable if the session ends midway.

## Phase 1 — Recon (parallel)

Decide targets first: the main URL at 1440px, plus 375px if responsive matters, plus any additional route the user asked for. Then spawn one `clone-recon` per target, **all in a single message so they run concurrently**.

Give each agent: the URL, its viewport width, the absolute project path, and its label (`desktop`, `mobile`, `pricing-desktop`).

When they return, verify the manifests before continuing: are the extract files non-empty, do the screenshot counts match the reported scroll height, did anyone hit a blocker? Recon failures are cheap to redo now and expensive to discover during verification. If an agent reports a login wall, paywall, or bot check, stop and tell the user — do not work around it.

## Phase 2 — Architecture (sequential)

Spawn one `clone-architect`. It reads all of `01-reference/` and `02-extract/` and produces the three planning files.

## Phase 3 — Checkpoint (mandatory)

Read `03-structure/STRUCTURE.md` yourself, then present it to the user in Korean: what the site is, the section list with measured heights, the derived design tokens, and — most importantly — everything under **불확실한 것**.

Ask them to confirm scope: which page(s), which viewport widths, how far to take interactions.

**Stop and wait for an answer.** This is the one blocking checkpoint in the workflow. Everything after it is expensive to redo, and a wrong assumption here means rebuilding every section.

## Phase 4 — Assets

Download what `STRUCTURE.md` classified as download-needed into `04-build/assets/`, via `curl`. Tell the user what you are fetching — filenames and source — before you fetch.

If an asset 403s or sits behind a CDN token, substitute a placeholder of the exact same dimensions and record the substitution in `NOTES.md`. Right-sized placeholders keep the layout honest; wrong-sized ones corrupt every measurement downstream.

## Phase 5 — Build (parallel)

Spawn one `clone-builder` per section from `SECTIONS.md`, **all in one message**. Each gets: the project path, its section id, and its full `SECTIONS.md` entry pasted inline.

Then assemble `04-build/index.html` yourself:
- `<!doctype html>`, `<head>` with charset, viewport meta, `<title>`, and the font `<link>`s from `fonts.json`
- A CSS reset, then `TOKENS.css` inline as `:root`
- Each section fragment concatenated in document order

You own this file. Builders never touch it.

## Phase 6 — Verify and iterate

Spawn `clone-verifier` agents — one per viewport width, or split by scroll band on a long page.

Read their defect lists, then dispatch fixes: one `clone-builder` per section that has defects, in parallel, each given only its own defect list. Reassemble. Verify again.

**Three rounds minimum.** Stop when a full verification pass returns nothing, not when it merely looks close. Save each round's report as `05-verify/round-N.md`.

If a section fails to converge after three rounds, stop iterating on it and surface it to the user with what you tried — grinding a fourth round on the same defect rarely works.

## Phase 7 — Hand off

Report in Korean:
- What was built and the absolute path to `index.html`
- Per-section match quality, honestly — name whatever is still off
- Every substitution: fonts, images, licensed assets, and why
- What was out of scope and what adding it would take

Finalize `NOTES.md`. Close every tab that is still open.

## When it goes sideways

Stop and ask rather than grinding — after 2–3 failed attempts at the same thing, or on any of:
- Login wall, paywall, or bot check (**never solve a CAPTCHA**)
- A page that renders nothing without JS you cannot trigger
- A section that will not converge after three verify rounds
- Fonts or images you can neither obtain nor reasonably substitute

Say what you tried, what is blocking, and what you would need to get past it.
