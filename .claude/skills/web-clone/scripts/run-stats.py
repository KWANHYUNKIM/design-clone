#!/usr/bin/env python3
"""Run cost report for a web-clone run: wall clock, tokens, agents, and questions asked.

Reads the Claude Code session transcript for the current project, including every
subagent transcript, and prints a markdown block to paste into RUN-LOG.md.

  python3 run-stats.py                      # whole session
  python3 run-stats.py --since 2026-08-12T14:03:00Z
  python3 run-stats.py --session <uuid>     # a specific session

The number that matters most is `questions asked`. This skill is supposed to run to
completion without handing anything back, so anything above zero is a defect to fix in
SKILL.md, not a statistic to accept.
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from glob import glob
from pathlib import Path

# Tools whose only purpose is to hand a decision back to the user.
ASK_TOOLS = {"AskUserQuestion", "ExitPlanMode"}

# Rough USD per million tokens. Override with --rates in:out:cache-write:cache-read.
DEFAULT_RATES = (5.0, 25.0, 6.25, 0.5)


def project_dir(cwd: Path) -> Path:
    slug = str(cwd).replace("/", "-")
    return Path.home() / ".claude" / "projects" / slug


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def walk(path, since):
    """Yield (timestamp, message dict) for every assistant/user entry in one transcript."""
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") not in ("assistant", "user"):
                continue
            stamp = parse_ts(entry.get("timestamp"))
            if since and stamp and stamp < since:
                continue
            yield entry.get("type"), stamp, entry.get("message") or {}


def collect(paths, since):
    stats = {
        "input": 0, "output": 0, "cache_write": 0, "cache_read": 0,
        "first": None, "last": None, "tools": Counter(), "questions": [],
        "user_turns": 0, "assistant_turns": 0,
    }
    for path in paths:
        for kind, stamp, message in walk(path, since):
            if stamp:
                if stats["first"] is None or stamp < stats["first"]:
                    stats["first"] = stamp
                if stats["last"] is None or stamp > stats["last"]:
                    stats["last"] = stamp
            if kind == "user":
                content = message.get("content")
                # A real user turn is plain text; tool results are lists of blocks.
                if isinstance(content, str) and content.strip():
                    stats["user_turns"] += 1
                continue
            stats["assistant_turns"] += 1
            usage = message.get("usage") or {}
            stats["input"] += usage.get("input_tokens", 0)
            stats["output"] += usage.get("output_tokens", 0)
            stats["cache_write"] += usage.get("cache_creation_input_tokens", 0)
            stats["cache_read"] += usage.get("cache_read_input_tokens", 0)
            blocks = message.get("content")
            if isinstance(blocks, list):
                for block in blocks:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "?")
                        stats["tools"][name] += 1
                        if name in ASK_TOOLS:
                            stats["questions"].append((stamp, name, block.get("input", {})))
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="ISO timestamp; ignore anything earlier")
    parser.add_argument("--session", help="session id (default: most recent)")
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--rates", help="in:out:cache_write:cache_read USD per 1M tokens")
    args = parser.parse_args()

    base = project_dir(Path(args.cwd).resolve())
    if not base.is_dir():
        sys.exit(f"no transcripts for {args.cwd} (looked in {base})")

    if args.session:
        main_log = base / f"{args.session}.jsonl"
    else:
        logs = sorted(glob(str(base / "*.jsonl")), key=os.path.getmtime)
        if not logs:
            sys.exit(f"no .jsonl transcripts in {base}")
        main_log = Path(logs[-1])
    if not main_log.exists():
        sys.exit(f"no such transcript: {main_log}")

    sub_dir = base / main_log.stem / "subagents"
    sub_logs = sorted(glob(str(sub_dir / "agent-*.jsonl")))
    since = parse_ts(args.since)

    overall = collect([main_log] + [Path(p) for p in sub_logs], since)
    rates = tuple(float(x) for x in args.rates.split(":")) if args.rates else DEFAULT_RATES

    agents = Counter()
    for meta_path in glob(str(sub_dir / "agent-*.meta.json")):
        try:
            agents[json.load(open(meta_path)).get("agentType", "?")] += 1
        except (OSError, json.JSONDecodeError):
            continue

    total_in = overall["input"] + overall["cache_write"] + overall["cache_read"]
    cost = (
        overall["input"] * rates[0] + overall["output"] * rates[1]
        + overall["cache_write"] * rates[2] + overall["cache_read"] * rates[3]
    ) / 1_000_000

    elapsed = "?"
    if overall["first"] and overall["last"]:
        minutes = (overall["last"] - overall["first"]).total_seconds() / 60
        elapsed = f"{minutes:.0f}분" if minutes < 90 else f"{minutes / 60:.1f}시간"

    print("## 실행 비용")
    print()
    print(f"- 세션: `{main_log.name}`" + (f", since `{args.since}`" if args.since else ""))
    print(f"- 경과: **{elapsed}**"
          + (f"  ({overall['first']:%H:%M} → {overall['last']:%H:%M} UTC)" if overall["first"] else ""))
    print(f"- 토큰: 입력 {total_in:,} (신규 {overall['input']:,} / 캐시쓰기 {overall['cache_write']:,}"
          f" / 캐시읽기 {overall['cache_read']:,}), 출력 {overall['output']:,}")
    print(f"- 추정 비용: **${cost:,.2f}**  (rates {':'.join(str(r) for r in rates)} per 1M)")
    print(f"- 어시스턴트 턴 {overall['assistant_turns']}, 도구 호출 {sum(overall['tools'].values())}")
    print(f"- 서브에이전트 {sum(agents.values())}개"
          + (f" — {', '.join(f'{k} x{v}' for k, v in agents.most_common())}" if agents else ""))
    print()
    print(f"- **사용자에게 물어본 횟수: {len(overall['questions'])}**"
          f"   (0이어야 정상 — 0이 아니면 SKILL.md를 고칠 것)")
    for stamp, name, payload in overall["questions"]:
        text = json.dumps(payload, ensure_ascii=False)[:160]
        when = f"{stamp:%H:%M}" if stamp else "?"
        print(f"  - `{when}` {name}: {text}")
    print(f"- 사용자 개입 턴 {overall['user_turns']}회 "
          f"(첫 요청 포함 — 2회 이상이면 자율 실행이 끊긴 것)")
    print()
    print("### 도구 사용 상위")
    for name, count in overall["tools"].most_common(10):
        print(f"- {name}: {count}")


if __name__ == "__main__":
    main()
