---
name: web-clone
description: Clone a website from a URL alone — its design pixel-for-pixel, and optionally its linked pages, its interactions, and the database schema behind them. Creates a per-project workspace, then orchestrates recon / architect / builder / analyst / verifier agents that drive Chrome to capture screenshots, extract real computed CSS (fonts, colors, spacing, grid), map routes and network traffic, build a self-contained index.html, and iterate clone-vs-original until they match. Trigger whenever the user supplies a URL and wants it recreated, copied, cloned, or rebuilt — even if they say nothing else, and including when they want the inner pages, the logic, or a DB modelled too.
---

# Web Clone — URL to pixel-identical HTML

The user gives **only a URL**. Everything else is yours: workspace, recon, screenshots, structure, build, verification. Never ask the user to take a screenshot or read a value off the page — you have Chrome.

You are the orchestrator. You do not do the capture or the typing yourself; you delegate to the agents below and own the plan, the checkpoint, and the final report.

Write files and internal notes in English. **Report to the user in Korean.**

## The agents

| Agent | Does | Parallelism |
|---|---|---|
| `clone-recon` | Drives Chrome: screenshots, computed-CSS extraction, content, routes | One per URL×viewport — parallel, each in its own tab |
| `clone-architect` | Reads capture → `STRUCTURE.md`, `SECTIONS.md`, `TOKENS.css` | One per project, sequential |
| `clone-builder` | Writes one section as an HTML fragment + scoped CSS | One per section — parallel, each owns one file |
| `clone-analyst` | **T3 only.** Drives the UI with network logging → `FLOWS.md`, `SCHEMA.md`, `schema.sql` | One per project, parallel with builders |
| `clone-verifier` | Screenshots the clone, diffs it against the original, reports defects | One per viewport or scroll band — parallel |

Parallelism is safe because each agent owns disjoint files and its own browser tab. It stops being safe the moment two agents write the same file — so builders write fragments and **you** assemble `index.html`.

## Ground rules

- **Measure, never eyeball.** A screenshot shows what it looks like; `getComputedStyle` says what it *is*. Guessing `#333` where the site uses `rgb(51, 51, 54)` is the single biggest source of "almost, but not quite".
- **Trust `innerWidth`, not `resize_window`.** The resize tool reports success even when the window did not move, so every capture width must be read back from the page before anything is saved. A mislabelled viewport poisons the whole run and only surfaces at verification. If the window will not resize (`outerWidth === 0` usually means Chrome is in macOS fullscreen), that needs the user — hand it to `access-gate` and, if they decline, **drop the viewport from scope rather than faking it**. Declared breakpoints can still be read statically at any width; how the layout actually reflows cannot.
- **One self-contained output**: `04-build/index.html`, inline `<style>`, no build step, no CDN. Assets in `04-build/assets/`.
- **Never invent content.** Real text, real hrefs, real images from the extraction. Lorem ipsum defeats the point.
- **Batch browser calls** with `browser_batch` — one call per scroll is slow.
- **Read-only browsing.** No sign-ups, purchases, or form submits. Cookie banners: choose the privacy-preserving option and say what was clicked. **Never solve a CAPTCHA.** The moment a login, paywall, bot check, or rate limit blocks the work, invoke the **`access-gate`** skill — it turns the wall into an explicit choice for the user instead of a silent gap.
- **Attribution.** This is a study reproduction. If the user wants to publish it, tell them to replace the brand name, logo, and copy first.

## How much to ask

Almost nothing. Work the problem to the end and report what you did.

The only things worth stopping for are the ones **no amount of your effort can produce**:
a password, a payment, a CAPTCHA, a browser window the tool cannot resize. Those go through
`access-gate`, and even then you finish everything unblocked first.

Everything else — which tier, which breakpoints, how to handle a licensed font, whether a
section is close enough — is yours to decide. Decide it, write down why, keep going. If a
run takes an hour of tool calls, that is the correct cost of the thing the user asked for.
Handing back a question is not a cheaper answer; it is no answer.

## Scope tiers

Infer the tier from the request and the site (see Phase 3). The cost between tiers is
roughly 10x, so say which one you picked — but pick it yourself.

| Tier | Output |
|---|---|
| **T1 — design** | One page, pixel-identical, static. **The default.** |
| **T2 — site** | Every in-scope route rebuilt, navigation between them works. Still static. |
| **T3 — app** | T2 plus working interactions, an inferred DB schema, seed data, local mock API. |

The phases below describe T1. For T2 or T3, read
`references/multipage-and-data.md` before planning — route discovery, crawl etiquette,
behaviour capture, and schema inference all have rules that do not appear here.

## Phase 0 — Project workspace

Every URL gets its own folder. Slug it from the domain plus page (`stripe-com-pricing`), and if that folder exists, suffix `-2`, `-3` — never overwrite a previous run.

```
projects/<slug>/
  01-reference/     original screenshots (desktop-01.png, mobile-01.png, *-detail-*, *-hover-*)
  02-extract/       raw computed CSS + content pulled from the live page — the evidence layer
  03-structure/     STRUCTURE.md, SECTIONS.md, TOKENS.css — the plan
  04-build/         index.html, sections/, assets/
  05-verify/        clone screenshots + defect reports per round
  06-model/         T3 only: raw network captures backing the schema inference
  NOTES.md          running log: URL, date, decisions, substitutions, blockers
```

Create all six (`06-model/` only for T3), then start `NOTES.md` with the URL, the date, and the user's stated scope. Every phase appends to it — it is what makes a run resumable if the session ends midway.

`NOTES.md` also records every **gate decision** from `access-gate`: what was blocked, what the user chose, what that left out.

## Phase 1 — Recon (parallel)

Decide targets first: the main URL at 1440px, plus 375px if responsive matters, plus any additional route the user asked for. Then spawn one `clone-recon` per target, **all in a single message so they run concurrently**.

Give each agent: the URL, its viewport width, the absolute project path, and its label (`desktop`, `mobile`, `pricing-desktop`).

When they return, verify the manifests before continuing: are the extract files non-empty, do the screenshot counts match the reported scroll height, did anyone hit a blocker? Recon failures are cheap to redo now and expensive to discover during verification. If an agent reports a login wall, paywall, or bot check, hand it to **`access-gate`** — do not work around it.

For T2/T3, this phase also produces the route inventory. One recon per *template*, not per URL, and sequential per host with a pause between — see `references/multipage-and-data.md`.

## Phase 2 — Architecture (sequential)

Spawn one `clone-architect`. It reads all of `01-reference/` and `02-extract/` and produces the three planning files.

## Phase 3 — Decide and keep going

**Do not stop here to ask permission.** The user asked for a clone; deciding how to build
it is the job, not a question to hand back. Read `03-structure/STRUCTURE.md`, make the
calls yourself from the evidence, write them into `NOTES.md`, tell the user what you
decided in two or three lines, and continue.

Defaults, unless the user said otherwise:

- **Tier** — infer it from what they asked for. "이 사이트 만들어줘" with linked nav and a
  product grid means they picture the inner pages working: go T2, and go T3 when the page
  is obviously data-driven (listings, filters, search results). A single marketing page
  with no list behind it is T1. When genuinely torn, take the *larger* scope — an extra
  route costs a cycle, a missed one costs the user their next request.
- **Viewports** — every width the site's own breakpoints declare and the browser can
  actually render. Drop a width only when it cannot be rendered, never to save effort.
- **Fonts** — hotlink what the site hotlinks; substitute only licensed faces you cannot
  reach, and name the substitution.
- **Assets** — download everything reachable; hotlink what 403s; placeholder at exact
  dimensions only as a last resort.

State assumptions in the report, in one line each. A stated assumption the user can
correct beats a question that stalls the work.

## Completeness gates — enforce these on yourself

Do not advance a phase until its gate passes. These are the failures that look like
success, so check them with commands, not with confidence.

**After recon**, before the architect sees anything:
- Screenshot count × viewport height ≥ `scrollHeight`. Missing tail = missing sections.
- `layout.txt` contains headings, `<img>`, and buttons — not just `<section>` wrappers.
  A skeleton that lists every section and nothing inside them is the classic plausible
  failure. Grep for it.
- Every extract file parses and is non-trivial. `{}` and error strings are failures.
- Section count in the capture matches what the geometry dump says exists.

**After the architect**: every section in `SECTIONS.md` has real measured numbers, and the
sum of section heights reconciles with the page's `scrollHeight`. If it does not, the plan
has a hole — find it now, not after six builders have worked from it.

**After the build**: the assembled page's height and each section's y-offset match the
original within a few px, measured by script on both pages.

When a gate fails, fix it and re-run the gate. Do not proceed with a note saying it was
close. Do not ask the user whether to proceed — they cannot see what you just measured.

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

## Phase 5.5 — Behaviour and data (T3 only)

Spawn `clone-analyst` once the routes are captured. It clicks through the real UI with
network logging on, and writes `FLOWS.md` (interactions) and `SCHEMA.md` (the inferred
data model) plus `04-build/db/schema.sql`.

Run it **after** Phase 3 and **in parallel with** the builders — it touches only its own
files, and its output is what the mock API is built against.

Read `references/multipage-and-data.md` before dispatching it. The two rules that matter
most: URL query params are the highest-value schema evidence on any site, and every field
must be marked `observed` or `inferred` — shipping a guessed schema as if it were
observed is the failure mode this whole phase exists to avoid.

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
- Every **gated** item as its own line — what was blocked and what the user chose. Never
  fold a gap into a success summary
- What was out of scope and what adding it would take

For T3, split the report three ways — **동작함** (built and verified), **관찰됨** (seen in
traffic, reproduced approximately), **추론임** (designed from evidence, never confirmed).
The schema is almost entirely the third, and saying so is the difference between a useful
deliverable and a misleading one.

Finalize `NOTES.md`. Close every tab that is still open.

## When it goes sideways

Change the approach rather than grinding the same one — and rather than handing the
problem back. A failed attempt is information about the method, not a reason to stop.

- **A subagent that has produced nothing useful for many minutes**: stop it and take the
  work yourself. A stalled agent is not progress, and its partial output is not evidence.
  Doing the capture inline is slower per call but it always terminates.
- **A script that times out**: the work often completed anyway — re-read the state in a
  separate short call before assuming failure. Split long loops into several calls.
- **A section that will not converge after three rounds**: build it from the screenshot
  by eye, mark it approximate in the report, and move on to the rest.
- **Fonts or images you cannot obtain**: substitute at exact dimensions, name the
  substitution, continue.

Genuinely stop only for a wall no effort of yours can pass — credentials, payment, a
CAPTCHA, a window the tool cannot resize. Those go to `access-gate`, and only after every
unblocked thing is finished.

A route disallowed by `robots.txt` or the ToS is not a wall to escalate — it is simply out
of scope. Note it and build the rest.
