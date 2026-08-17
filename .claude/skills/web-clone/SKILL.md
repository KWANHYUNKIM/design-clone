---
name: web-clone
description: Clone a website from a URL alone — its design pixel-for-pixel, its linked pages, and optionally its interactions and the database schema behind them. Creates a per-project workspace, then screenshots the entire site depth-first (landing page, every nav destination, their children) into one folder per page, extracts real computed CSS (fonts, colors, spacing, grid), factors the repeated blocks into shared modules, and orchestrates crawler / recon / architect / builder / analyst / verifier agents that build self-contained HTML and iterate clone-vs-original until they match. Trigger whenever the user supplies a URL and wants it recreated, copied, cloned, rebuilt, or captured — even if they say nothing else, and including when they want the inner pages, the logic, or a DB modelled too.
---

# Web Clone — URL to pixel-identical HTML

The user gives **only a URL**. Everything else is yours: workspace, recon, screenshots, structure, build, verification. Never ask the user to take a screenshot or read a value off the page — you have Chrome.

You are the orchestrator. You do not do the capture or the typing yourself; you delegate to the agents below and own the plan, the decisions, and the final report. **There is no user checkpoint anywhere in this run** — you decide, log it in `NOTES.md`, and keep going until Phase 9. If you find yourself writing a question to the user before Phase 9, that is a bug: answer it from the evidence instead.

Write files and internal notes in English. **Report to the user in Korean.**

## The agents

| Agent | Does | Parallelism |
|---|---|---|
| `clone-crawler` | **Screenshots every page, depth-first through the nav**, one folder each | One per top-level nav branch — parallel, each in its own tab |
| `clone-recon` | Deep capture of one page: computed CSS, content, assets, geometry | One per template×viewport — parallel, each in its own tab |
| `clone-architect` | Reads capture → `STRUCTURE.md`, `MODULES.md`, `SECTIONS.md`, `TOKENS.css` | One per project, sequential |
| `clone-builder` | Writes one section as an HTML fragment + scoped CSS | One per section — parallel, each owns one file |
| `clone-analyst` | **T3 only.** Drives the UI with network logging → `FLOWS.md`, `SCHEMA.md`, `schema.sql` | One per project, parallel with builders |
| `clone-verifier` | Screenshots the clone, diffs it against the original, reports defects | One per page×viewport or scroll band — parallel |
| `clone-finisher` | **Walks the finished clone like a user and fixes what is broken** | One per viewport — parallel, last phase before handoff |

Parallelism is safe because each agent owns disjoint files and its own browser tab. It stops being safe the moment two agents write the same file — so builders write fragments and **you** assemble `index.html`.

## Ground rules

- **Screenshot everything, first.** Before any planning, the whole site is on disk as
  images: the landing page, then every nav destination, then *their* children,
  depth-first, one folder per page. Every later phase is reconstruction from those
  folders — a page nobody screenshotted is a page the clone will not have. When budget is
  tight, cut extraction depth, never screenshot coverage.
- **Build from modules, not from pages.** The header on page 7 is the same header as on
  page 1. Capture that fact once (`MODULES.md`), build it once, compose every page from
  it. Rebuilding the nav per page is how a clone ends up subtly different on every route.
- **Measure, never eyeball.** A screenshot shows what it looks like; `getComputedStyle` says what it *is*. Guessing `#333` where the site uses `rgb(51, 51, 54)` is the single biggest source of "almost, but not quite".
- **Trust `innerWidth`, not `resize_window`.** The resize tool reports success even when the window did not move, so every capture width must be read back from the page before anything is saved. A mislabelled viewport poisons the whole run and only surfaces at verification. If the window will not resize (`outerWidth === 0` usually means Chrome is in macOS fullscreen), that needs the user — hand it to `access-gate` and, if they decline, **drop the viewport from scope rather than faking it**. Declared breakpoints can still be read statically at any width; how the layout actually reflows cannot.
- **Self-contained output**: `04-build/index.html` plus one folder per route, inline `<style>`, no build step, no CDN. Assets in `04-build/assets/`, shared blocks in `04-build/modules/`. It opens from the filesystem with no server.
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

**Do not end your turn between phases.** Reporting progress is not a stopping point:
when agents return, read their output and dispatch the next phase in the same turn. The
only turn that ends with the work unfinished is one blocked by `access-gate`. Phase 9 is
the finish line — everything before it is mid-sentence.

## Scope tiers

Infer the tier from the request and the site (see Phase 3). The cost between tiers is
roughly 10x, so say which one you picked — but pick it yourself.

**The crawl is not tiered.** Phase 1a screenshots the whole site at every tier, including
T1 — the tier decides how much of it gets *built*, never how much gets captured. A T1 run
still hands back a complete `01-reference/` tree, which is what makes the next request
cheap instead of a restart.

| Tier | Output |
|---|---|
| **T1 — design** | The landing page rebuilt pixel-identical, static — plus the full screenshot map of everything else. |
| **T2 — site** | Every in-scope route rebuilt, navigation between them works. Still static. |
| **T3 — app** | T2 plus client-side interactions, and an inferred DB schema **documented, not implemented** — no server, no seed data. |

The phases below describe T1. For T2 or T3, read
`references/multipage-and-data.md` before planning — route discovery, crawl etiquette,
behaviour capture, and schema inference all have rules that do not appear here.

## Phase 0 — Project workspace

Every URL gets its own folder. Slug it from the domain plus page (`stripe-com-pricing`), and if that folder exists, suffix `-2`, `-3` — never overwrite a previous run.

```
projects/<slug>/
  01-reference/     one folder per page, in depth-first visit order — the evidence that matters most
    MAP.md            the site tree: page → children, folder → URL, what was skipped
    00-home/          <label>-full-01.png…, <label>-nav.png, <label>-hover-*.png, page.json
    01-products/
    01-01-products-shoes/
    02-about/
  02-extract/       raw computed CSS + content, one set per template — the measurement layer
  03-structure/     STRUCTURE.md, MODULES.md, SECTIONS.md, ACTIONS.md, TOKENS.css — the plan
  04-build/         index.html, modules/, <route>/, assets/, js/actions.js
  05-verify/        clone screenshots + defect reports per round
  06-model/         T3 only: raw network captures backing the schema inference
  NOTES.md          running log: URL, date, decisions, substitutions, blockers
  RUN-LOG.md        cost record: start time, per-phase elapsed, questions asked, final totals
```

Create all six (`06-model/` only for T3), then start `NOTES.md` with the URL, the date, and the user's stated scope. Every phase appends to it — it is what makes a run resumable if the session ends midway.

Also start **`RUN-LOG.md`** — the cost record for this run. First line is the start
timestamp from `date -u +%Y-%m-%dT%H:%M:%SZ`; keep it, Phase 9 needs it.

`01-reference/` is the deliverable's backbone even when the build goes wrong. Keep it complete and keep its folder names stable; `MAP.md`, `MODULES.md`, and every `page.json` reference them by name.

**Never touch `.gitignore`.** No `projects/` entry, no per-project entry, no "just the big
PNGs". `.gitignore` is committed and shared; a clone run is neither. If you find such an
entry there, remove it and say so.

Clone runs stay out of git **locally** instead, via `.git/info/exclude` — untracked,
machine-local, nobody else's repo affected. Once per repo, append:

```
# Clone runs: kept out of git locally, never via .gitignore
projects/
```

Check it is there at Phase 0 and add it if it is not. Then `git status` stays readable and
no run ever gets committed by accident. The screenshots still live on disk and are still
the deliverable — tell the user the absolute path at handoff, since it will never show up
in a diff.

`NOTES.md` also records every **gate decision** from `access-gate`: what was blocked, what the user chose, what that left out.

## Phase 1a — Screenshot crawl (parallel branches, depth-first inside each)

**This is the phase that decides whether the clone is any good.** Do it before anything
else and do not economise on it.

**Measure the capture width in a tab you created with `tabs_create_mcp`** — the same way
agents create theirs — and pass that number to every agent. Do *not* trust the tab
`tabs_context_mcp{createIfEmpty:true}` hands you: it can live in a different window and
report a different width, and then every agent you dispatch is working from a false
constant. (Observed: orchestrator tab 1920, every agent tab 1600.)

Open the landing page yourself first — one `clone-crawler` for the root, or a quick
`navigate` + `read_page{filter:"interactive"}` — and read the primary navigation. Each
top-level nav item is a **branch**.

Two rules for the dispatch itself, both learned the hard way:
- **Never `SendMessage` a crawler that is mid-capture** to change its parameters. A stopped
  agent resumes cleanly; a running one is checkpointed and often cannot be resumed, and you
  lose everything it had not yet written. Let it finish, or kill it and re-dispatch.
- **Do not keep a working tab of your own while crawlers run.** The MCP tab group gets torn
  down and recreated under concurrency, and every extra tab raises the rate. Four
  concurrent crawlers is a practical ceiling. When any browser call fails with a target/tab
  error, call `tabs_context_mcp` and re-acquire ids rather than retrying the stale one.

Then spawn one `clone-crawler` per branch, **all in one message**, each with: the project
path, the origin, its branch root URL and label, the viewport width, its numbering prefix
(`01`, `02`, …), the max depth, its page budget, and the URLs other crawlers have claimed
so two agents never capture the same page.

Each crawler goes *down* before it goes *across*: nav item → that page's children →
their children, to the leaf, then backtrack. Sensible defaults: depth 3, ~15 pages per
branch, at most 3 pages per repeated template. Raise them for a small site; say in
`NOTES.md` what you set and why.

`MAP.md` is **generated, not hand-written** — crawlers land folder by folder and some of
them die and get re-dispatched, so you want to refresh it against disk at any moment:

```bash
python3 .claude/skills/web-clone/scripts/build-map.py projects/<slug>
```

It reads every `page.json`, writes the tree, groups pages by signature into the template
list that Phase 1b works from, runs the coverage gate, and names any folder holding
screenshots with no `page.json` — the signature of a crawler that died mid-page. Run it
after each crawler returns. **You own `MAP.md`**; crawlers own only their own folders.

Then check the crawl before spending anything else on it:
- Every branch of the nav appears in the tree. A missing branch means a crawler died —
  respawn it, do not proceed.
- Every page folder has a `page.json` and at least one `-full-01.png`.
- Shots × viewport height ≥ `scrollHeight` per page. Short means a truncated page.
- Spot-read four or five screenshots across different depths with the Read tool. Blank or
  banner-covered renders pass every automated check and fail the build.

If a crawler reports a login wall, paywall, or bot check, hand it to **`access-gate`** —
do not work around it.

## Phase 1b — Deep extraction (parallel)

Group the captured pages by their `page.json` signature. **One `clone-recon` per distinct
template per viewport**, not per page — twenty product pages share one set of measurements.

Spawn them all in one message, each with: the URL of that template's representative page,
its viewport width, the project path, and its label (`home-desktop`, `product-mobile`).
Widths: 1440px always, 375px whenever the site declares a mobile breakpoint.

Verify the manifests before continuing — extract files non-empty, `layout.txt` containing
real content and not just section wrappers, no blockers. Recon failures are cheap to redo
now and expensive to discover during verification.

## Phase 2 — Architecture (sequential)

Spawn one `clone-architect`. It reads `MAP.md`, every `page.json`, the screenshots, and
all of `02-extract/`, and produces the four planning files.

The one that changes the outcome most is **`MODULES.md`**: every block that appears on two
or more pages — header, nav, footer, card, form, CTA — defined once, with its measured
values and the list of pages that use it. Page entries in `SECTIONS.md` then read as
"modules `header`, `hero`, `card-grid`, `footer`, plus these page-specific sections".
Build each module once and every page inherits the same one.

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

## Run log — measure the run, not just the clone

`RUN-LOG.md` exists so this skill can be improved from evidence instead of impressions.
Keep it as you go; it costs one line per phase.

**At the end of each phase**, append one line: phase, wall-clock elapsed, agents spawned,
and anything that went wrong — a gate that failed, an agent respawned, a retry loop, a
tool that kept erroring. Those lines are the raw material for the next revision of this
file, so name the friction rather than smoothing over it.

**Log every question you ask the user, verbatim, with the phase it happened in.** The
target is zero: this skill is written to run to completion on a URL alone. A question is a
defect in these instructions — record what you needed and could not derive, so the gap
gets closed instead of re-asked next run.

**At Phase 9**, generate the totals:

```bash
python3 .claude/skills/web-clone/scripts/run-stats.py --since <start timestamp from RUN-LOG.md>
```

It reads the session transcript and every subagent transcript and reports elapsed time,
token totals, estimated cost, subagent counts by type, tool-call counts, and the number of
questions asked. Paste its markdown output at the bottom of `RUN-LOG.md`, then put the
three headline numbers — 소요 시간, 예상 비용, 질문 횟수 — in the handoff report.

If the script's question count disagrees with your own log, the script is right: it counts
`AskUserQuestion` calls from the transcript, and it also counts user turns, which catches
the softer failure of ending a turn mid-run and waiting.

## Completeness gates — enforce these on yourself

Do not advance a phase until its gate passes. These are the failures that look like
success, so check them with commands, not with confidence.

**After the crawl**, before any extraction is spent — `build-map.py` checks the first three
for you:
- Every top-level nav item has a folder. Count the nav links, count the branches, compare.
- Every folder has `page.json` and `-full-01.png`.
- Coverage: shots × viewport height ≥ `scrollHeight`, **or** the page is legitimately
  capped — an infinite feed whose `page.json` records the deliberate truncation, or a
  `template-duplicate` that only had to prove which template it is. Write the gate this way
  or it fails on pages that are correct, and a gate that cries wolf is one you learn to
  wave through. Only an undocumented shortfall is a defect.
- Every distinct signature has a representative folder — that list *is* the template list.
- Read four or five screenshots yourself, spread across depths. Blanks pass every other check.

**After extraction**, before the architect sees anything:
- `layout.txt` contains headings, `<img>`, and buttons — not just `<section>` wrappers.
  A skeleton that lists every section and nothing inside them is the classic plausible
  failure. Grep for it.
- Every extract file parses and is non-trivial. `{}` and error strings are failures.
- Section count in the capture matches what the geometry dump says exists.
- Every template signature from `MAP.md` has an extract set. A template with screenshots
  but no measurements will be built by eye — catch that now.

**After the architect**: every section in `SECTIONS.md` has real measured numbers, and the
sum of section heights reconciles with each page's `scrollHeight`. Every block appearing in
two or more `page.json` files is in `MODULES.md` — a repeated block that is not a module
will be rebuilt inconsistently on every page.

**After the build**: the assembled page's height and each section's y-offset match the
original within a few px, measured by script on both pages.

**Before handoff** — the gate that no run may skip: a `clone-finisher` has walked every
built page at every viewport, its last pass found nothing new, and no console error, dead
link, or dead action remains unexplained. A clone nobody clicked through is not finished,
however good its screenshots look.

When a gate fails, fix it and re-run the gate. Do not proceed with a note saying it was
close. Do not ask the user whether to proceed — they cannot see what you just measured.

## Phase 4 — Assets

Download what `STRUCTURE.md` classified as download-needed into `04-build/assets/`, via `curl`. Log what you fetched — filenames and source — to `NOTES.md`, and list it in the Phase 9 report. Do not announce the list mid-run and wait; there is nothing for the user to approve here.

If an asset 403s or sits behind a CDN token, substitute a placeholder of the exact same dimensions and record the substitution in `NOTES.md`. Right-sized placeholders keep the layout honest; wrong-sized ones corrupt every measurement downstream.

## Phase 5 — Build (parallel, modules first)

**Round 1 — modules.** Spawn one `clone-builder` per entry in `MODULES.md`, all in one
message. Each writes `04-build/modules/<name>.html` and its scoped CSS, and is told which
pages use it. These are shared, so they are built before anything that depends on them.

**Round 2 — page-specific sections.** Spawn one `clone-builder` per remaining section in
`SECTIONS.md`, all in one message. Each gets: the project path, its section id, its full
`SECTIONS.md` entry pasted inline, and the reference folder its page came from. Builders
never rebuild a module — they reference it by name.

Then assemble the pages yourself — `04-build/index.html` for the landing page and
`04-build/<route>/index.html` for every other captured page:
- `<!doctype html>`, `<head>` with charset, viewport meta, `<title>`, and the font `<link>`s from `fonts.json`
- A CSS reset, then `TOKENS.css` inline as `:root`, then every module's CSS, then the page's own
- Modules and sections concatenated in the order that page's `page.json` records
- Nav `href`s rewritten to the local route folders, so the clone navigates like the original

You own these files. Builders never touch them.

Pages that shared a signature share their build: one template, filled with each page's own
captured content. That is the point of the module layer — twelve product pages are one
build, not twelve.

## Phase 5.5 — Behaviour and data (T3 only)

Spawn `clone-analyst` once the routes are captured. It clicks through the real UI with
network logging on, and writes `FLOWS.md` (interactions) and `SCHEMA.md` (the inferred
data model) plus `04-build/db/schema.sql`.

This phase is **documentation only**. No server, no seed data, no wiring the page to an
API — `04-build/db/schema.sql` is a DDL file to read, not something the clone runs
against. The clone stays static, so `index.html` stays self-contained.

Run it **after** Phase 3 and **in parallel with** the builders — it touches only its own
files.

Read `references/multipage-and-data.md` before dispatching it. The two rules that matter
most: URL query params are the highest-value schema evidence on any site, and every field
must be marked `observed` or `inferred` — shipping a guessed schema as if it were
observed is the failure mode this whole phase exists to avoid.

## Phase 6 — Verify and iterate

Spawn `clone-verifier` agents — one per built page per viewport, or split by scroll band on
a long page. Each diffs its page against **that page's own folder** in `01-reference/`, not
against the landing page. The reference shots are the answer key; this phase is just
checking your work against it.

Read their defect lists, then dispatch fixes: one `clone-builder` per section that has
defects, in parallel, each given only its own defect list. **A defect in a module is fixed
once** — check whether the same defect appears on other pages before treating it as
page-specific; if it does, it belongs to the module. Reassemble. Verify again.

**Three rounds minimum.** Stop when a full verification pass returns nothing, not when it merely looks close. Save each round's report as `05-verify/round-N.md`.

If a section fails to converge after three rounds, stop iterating on it and surface it to the user with what you tried — grinding a fourth round on the same defect rarely works.

## Phase 7 — 액션 (make it work, not just look right)

A clone that renders perfectly and does nothing when clicked is half a clone. This phase is
not optional and it is not T3-only.

Work from `03-structure/ACTIONS.md` — the interaction list the architect derived from the
hover shots, the interactive dumps, and `FLOWS.md` when it exists. Spawn one `clone-builder`
to write `04-build/js/actions.js`: **vanilla JS, no framework, no CDN**, one small handler
per action, each commented with the entry it implements.

The usual set, when the original has them: sticky/shrinking header, mobile hamburger drawer,
dropdown menus, tabs, accordions, carousels, modals, filter chips, back-to-top, scroll
reveals. Match the original's timing and easing — the numbers are in the entry.

Two rules:
- **Only what was observed.** No interaction that a hover shot, the interactive dump, or
  `FLOWS.md` does not evidence. Inventing a slick animation the site does not have makes
  the clone *less* accurate, however good it looks.
- **Degrade honestly.** An interaction you cannot reproduce (a server-backed search, an
  A/B-gated flow) stays out, with a line in `NOTES.md`. Never fake it with a stub that
  looks alive.

Reference `js/actions.js` from every assembled page, and re-run the affected pages through
a verifier if the actions changed layout.

## Phase 8 — 최종 점검 세션 (walk it and fix it)

**This phase is mandatory and it is never skipped, however well Phase 6 went.** Everything
before it checked one piece against one reference. Nothing so far has opened the finished
clone and *used* it.

Spawn `clone-finisher` — one per viewport width — after the actions are wired. Each walks
every built page at its width: console, every link, every action, hover states, horizontal
overflow, mobile menu. Unlike the verifier, it **fixes what it finds in place** and
re-checks, looping until a full pass comes back clean or three passes are done.

When they return:
- Dispatch a `clone-builder` for anything they handed back as needing a section rebuild,
  then run a finisher again over those pages. Do not hand back to the user instead.
- Read the remaining console errors yourself. "Some 404s on decorative images" is a
  sentence that has ended many runs one step short of done.
- Only then write the handoff.

The one thing you may not do is report a clone as finished that no one ever clicked
through. If the finishers could not run — no browser, blocked window — say exactly that in
the report rather than letting the silence read as success.

## Phase 9 — Hand off

Report in Korean:
- The captured site map: how many pages screenshotted, how deep, how many templates —
  and the absolute path to `01-reference/`
- What was built and the absolute path to `index.html`, plus the route folders
- The module list, and which pages each module serves
- Per-page and per-section match quality, honestly — name whatever is still off
- **동작 확인 결과**: which actions work, which were left out and why, and what the final
  walkthrough fixed. Say plainly if any page was never clicked through
- Pages that were screenshotted but not built, and what building them would take
- Every substitution: fonts, images, licensed assets, and why
- Every **gated** item as its own line — what was blocked and what the user chose. Never
  fold a gap into a success summary
- What was out of scope and what adding it would take
- **실행 비용 세 줄**: 소요 시간, 예상 비용, 사용자에게 물어본 횟수 — from `RUN-LOG.md`.
  Report the question count even when it is zero; that is the number this skill is tuned
  against, and a run that hid it cannot be improved.

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
