#!/usr/bin/env python3
"""Regenerate 01-reference/MAP.md from the crawlers' page.json files.

  python3 build-map.py <project-dir>

The orchestrator owns MAP.md; crawlers own only their own folders. Because a crawl lands
folder by folder — and because crawlers die and get re-dispatched — MAP.md is worth
generating rather than hand-writing, so it can be refreshed at any moment for the current
state of disk.

It also runs the coverage gate: shots x viewportHeight >= scrollHeight, EXCEPT where the
page's own notes record a deliberate truncation (infinite feeds), which is reported as
CAPPED rather than SHORT. A folder with screenshots but no page.json is reported as
INCOMPLETE — those are the remains of a crawler that died mid-page.
"""

import json
import re
import sys
from glob import glob
from pathlib import Path
from urllib.parse import urlsplit

# Viewport height and scrollY are read as integers but are fractional under a non-integer
# devicePixelRatio or zoom, so an exactly-complete capture can score 1px short per rounded
# measurement. Tolerate a few px; a genuinely missing tail is hundreds of px, never four.
ROUNDING_SLACK = 4

TRUNCATION_HINTS = (
    "infinite", "not paged", "NOT paged", "capped", "deliberate",
    "per instructions", "do not page", "stopped paging",
)


def normalize_sig(sig):
    """Group templates by shape, not by how many cards happened to be mounted.

    Crawlers write counts into the signature (`card-grid(6-up,infinite)`, `carousel(xN)`),
    which is useful detail but splits one template into several when two captures of the
    same page hydrated differently. Strip the parentheticals and the digits before
    grouping; the representative keeps its full signature for the architect to read.
    """
    sig = re.sub(r"\([^)]*\)", "", sig or "")
    sig = re.sub(r"\d+", "", sig)
    return re.sub(r"\s+", "", sig).strip(">").lower()


def viewport_height(data):
    """The viewport height this page was captured at, however the crawler spelled it.

    The coverage gate is shots x viewportHeight >= scrollHeight, so this number decides
    every SHORT/OK verdict. Crawlers have written it four different ways in practice —
    top-level `viewportHeight` or `innerHeight`, and nested `viewport.height` or
    `viewport.innerHeight` — and a spelling this function does not know silently falls
    back to a default, marking well-covered pages SHORT across the whole run. Read every
    spelling before giving up, and make the fallback loud rather than plausible.
    """
    for key in ("viewportHeight", "innerHeight", "viewport_height"):
        if isinstance(data.get(key), (int, float)) and data[key] > 0:
            return data[key]
    vp = data.get("viewport")
    if isinstance(vp, dict):
        for key in ("height", "innerHeight", "h"):
            if isinstance(vp.get(key), (int, float)) and vp[key] > 0:
                return vp[key]
    return None


def target_height(data):
    """The page height the capture actually had to cover.

    `scrollHeight` is usually sampled on arrival, but these pages are not static: lazy
    sections settle, skeletons collapse, and a page can be materially SHORTER by the time
    the last shot is taken (one lookbook went 6536 -> 5710). Gating a complete capture
    against a stale first-paint height reports a missing tail that never existed.

    When the crawler recorded the height at the bottom, that is the honest target — it is
    the height that was true when the sweep finished. Infinite feeds grow instead of
    shrinking, but those are caught by the truncation hints, not by this number.
    """
    for key in ("scrollHeight_at_bottom", "scrollHeightAtBottom", "settledScrollHeight",
                "scrollHeight_settled"):
        if isinstance(data.get(key), (int, float)) and data[key] > 0:
            return data[key]
    return data.get("scrollHeight", 0)


def coverage(data, n_shots, vh):
    """How far down the page the shots actually reach, in px.

    `n_shots * vh` assumes the shots tile the page without overlap, which is wrong at the
    bottom: the browser clamps scrollTo to `scrollHeight - vh`, so the last shot always
    overlaps its predecessor on a page that is not an exact multiple of the viewport. That
    made short pages fail the gate by the size of the remainder (a 1559px page captured in
    full at scrollY 0 and 786 scored 1546/1559) — a defect that is pure arithmetic, and
    indistinguishable in the report from a genuinely missing tail.

    When the crawler recorded where each shot was taken, measure from that instead; it is
    exact and handles clamping, overlap, and gap-fill shots for free.
    """
    positions = data.get("shotScrollY") or data.get("shot_scroll_map")
    if isinstance(positions, dict):
        positions = list(positions.values())
    if isinstance(positions, list):
        ys = [y for y in positions if isinstance(y, (int, float))]
        if ys:
            return max(ys) + vh
    return n_shots * vh


def depth_of(folder):
    """DFS depth from the numbering prefix: 00 -> 0, 00-01 -> 1, 00-01-01 -> 2."""
    parts = re.match(r"^([\d-]+?)-[a-z]", folder + "-x")
    if not parts:
        return 0
    return max(0, len([p for p in parts.group(1).split("-") if p.isdigit()]) - 1)


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    ref = root / "01-reference"
    if not ref.is_dir():
        sys.exit(f"no 01-reference/ under {root}")

    rows, orphans, sigs = [], [], {}
    for folder in sorted(p for p in ref.iterdir() if p.is_dir()):
        shots = sorted(glob(str(folder / "*full*.png")))
        meta = folder / "page.json"
        if not meta.exists():
            orphans.append((folder.name, len(shots)))
            continue
        try:
            data = json.loads(meta.read_text())
        except json.JSONDecodeError as exc:
            orphans.append((folder.name, f"page.json unparseable: {exc}"))
            continue

        vh = viewport_height(data)
        sh = target_height(data)
        notes = str(data.get("notes", ""))
        status = data.get("status", "?")
        if vh is None:
            # Never guess a height here. A wrong one turns the gate into noise in whichever
            # direction the guess leans, and the failure looks exactly like a real gap.
            covered = 0
            gate = "NO-VIEWPORT"
        elif (covered := coverage(data, len(shots), vh)) >= sh - ROUNDING_SLACK:
            gate = "OK"
        elif status == "template-duplicate":
            # Short by design: a duplicate only has to prove which template it is.
            gate = "CAPPED dup"
        elif any(h.lower() in notes.lower() for h in TRUNCATION_HINTS):
            gate = "CAPPED"
        else:
            gate = f"SHORT {covered}/{sh}"

        url = data.get("resolvedUrl") or data.get("url", "")
        sig = data.get("signature", "")
        sigs.setdefault(normalize_sig(sig), []).append((folder.name, sig))
        rows.append({
            "folder": folder.name,
            "depth": data.get("depth", depth_of(folder.name)),
            "path": urlsplit(url).path or "/",
            "shots": len(shots),
            "sh": sh,
            "gate": gate,
            "sig": sig,
            "status": status,
        })

    out = ["# Site map — captured pages", ""]
    out.append(f"{len(rows)} pages captured, {len(sigs)} distinct template signatures, "
               f"{sum(r['shots'] for r in rows)} full-page screenshots.")
    out.append("")
    out.append("| folder | depth | path | shots | scrollH | gate | status |")
    out.append("|---|---|---|---|---|---|---|")
    for r in rows:
        out.append(f"| `{r['folder']}` | {r['depth']} | `{r['path']}` | {r['shots']} | "
                   f"{r['sh']} | {r['gate']} | {r['status']} |")

    out += ["", "## Templates", "",
            "One representative per signature — this list is the Phase 1b extraction "
            "work list.", ""]
    for i, (_, members) in enumerate(sorted(sigs.items(), key=lambda kv: -len(kv[1])), 1):
        rep, rep_sig = members[0]
        others = [m[0] for m in members[1:]]
        out.append(f"**T{i}** — representative `{rep}`"
                   + (f", also {', '.join('`' + f + '`' for f in others)}" if others else ""))
        out.append(f"  - `{rep_sig[:400]}`")
        out.append("")

    if orphans:
        out += ["## INCOMPLETE — screenshots but no usable page.json", "",
                "A crawler died mid-page here. Either re-dispatch for these or delete the "
                "stray shots; a folder in this state is nearly useless downstream.", ""]
        for name, n in orphans:
            out.append(f"- `{name}` — {n} shots" if isinstance(n, int) else f"- `{name}` — {n}")
        out.append("")

    (ref / "MAP.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {ref / 'MAP.md'}: {len(rows)} pages, {len(sigs)} templates, "
          f"{len(orphans)} incomplete")
    for r in rows:
        if r["gate"].startswith(("SHORT", "NO-VIEWPORT")):
            print(f"  GATE FAIL {r['folder']}: {r['gate']}")


if __name__ == "__main__":
    main()
