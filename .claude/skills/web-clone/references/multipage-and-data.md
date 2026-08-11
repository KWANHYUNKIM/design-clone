# Beyond the landing page — routes, behaviour, and the data model

Read this when the user wants more than one page's pixels: the linked sections
(`/products`, `/community`, `/jobs`…) rebuilt too, the interactions working, and a
database behind it. The base `SKILL.md` flow still runs — this adds three things to it:
**route coverage**, **behaviour reverse-engineering**, and **schema inference**.

Everything here is inference from the outside. You are reading a black box through its
HTML, its URLs, and its network traffic. Label what you observed and what you guessed,
and never let the two blur together.

## Pick a tier before you start

Confirm the tier at the Phase 3 checkpoint — the cost difference between them is 10x.

| Tier | Output | Cost |
|---|---|---|
| **T1 — design** | One page, pixel-identical, static. The `SKILL.md` default. | baseline |
| **T2 — site** | Every in-scope route, real navigation between them, still static. | ~1 recon+build cycle per route |
| **T3 — app** | T2 plus working interactions, a schema, seed data, and a local mock API. | ~2x T2, plus backend work |

T3 does **not** mean a working product. It means a convincing local reproduction:
filters that filter, search that searches, detail pages that read from a real table.
Payments, messaging, notifications, real auth — out of scope unless the user names them.

## Route discovery

Cast the net before choosing:

1. `<label>-interactive.txt` from recon — every `<a href>` already captured
2. `/sitemap.xml` and `/robots.txt` — fetch with `curl`, not the browser
3. The nav and footer specifically — those are the site's own map of itself
4. Framework route manifests when the site is a SPA: Next.js `__NEXT_DATA__`,
   Remix `window.__remixManifest`, Nuxt `__NUXT__`. Read them via `javascript_tool`.

Then **collapse URLs into templates**. A marketplace with 40,000 listings has maybe six
templates. `/kr/buy-sell/s/`, `/kr/cars/s/`, `/kr/jobs/s/` are one *list* template with a
category param; `/kr/community/<slug>-<id>/` is one *detail* template.

Write `03-structure/ROUTES.md`:

| pattern | template | example URL | in scope | needs auth |
|---|---|---|---|---|
| `/kr/<cat>/s/` | list+filter | `/kr/buy-sell/s/` | yes | no |
| `/kr/community/<slug>/` | detail | `…-vj4vyx2v34da/` | yes | no |
| `/kr/chat/*` | app | — | no | **yes** |

**Clone templates, not URLs.** One list page and two or three detail pages per template
is enough to derive both the layout and the schema. Recon every listing and you burn the
budget on redundant captures — and hammer someone's server for nothing.

## Crawl etiquette — non-negotiable

- Read `/robots.txt` first and honour it. A `Disallow` is a stop sign, not a hint.
- One page at a time per host, with a pause between. Parallel recon agents are for
  *viewports of one page*, not for twenty pages of one host at once.
- Stop immediately on `429`, `403`, or a bot-check interstitial. Do not retry harder,
  do not rotate anything. Escalate via the `access-gate` skill.
- Never capture other people's personal data — profile names, phone numbers, emails,
  precise locations, message content. If a page is full of it, capture the *layout* and
  replace the values with synthetic ones. Record the substitution.
- Public listing pages only. Anything behind a login is `access-gate` territory.

## Behaviour: read the URL, then the network

Interactions are usually legible from two sources, in this order of reliability:

**1. The URL.** Filters, sorts, pagination and search almost always serialize into the
query string, and that string is a near-verbatim description of the backend query:

```
/kr/realty/s/?salesType=one_room     → column salesType,  enum value one_room
/kr/cars/s/?company=1                → FK  company_id,    integer key
/kr/jobs/s/?tasks=SERVING            → column tasks,      enum value SERVING
/kr/buy-sell/s/?search=<encoded>     → full-text search on the listing table
```

Collect every distinct param across every captured route. Each one is a column, a filter,
or a join — and the set of values a `<select>` or filter chip offers is the enum's full
domain, handed to you for free.

**2. The network.** With `read_network_requests`, click through the real UI — open a
filter, page forward, submit a search — and read what fires. A JSON endpoint returns the
entity almost exactly as the database holds it: field names, types, nulls, nested
relations, pagination shape (`cursor` vs `offset` tells you how to index).

Note the shape, not the payload. You want `{ id, title, price, region_id, created_at }` —
you do not want ten thousand rows of someone's listings.

Write `03-structure/FLOWS.md`: one entry per interaction — trigger, what changes in the
URL, what request fires, what comes back, what the UI does with it, and the empty /
loading / error states if you can reach them.

## Schema inference

Work from the rendered page backwards. Every repeated card is a row; every field on the
card is a column; every link between two templates is a foreign key.

**Entities** — one per detail template, plus every noun that has its own list page.

**Columns** — from three sources: fields visible on the card, fields visible only on the
detail page (so: nullable on the list query, not on the table), and params in the URL.

**Types** — infer from the rendered format, then widen for safety.
`6일 전` is a `timestamptz` rendered relatively, not a string. `375-87-00088` is `text`,
not a number — it has leading-zero and hyphen semantics. Money is `numeric`, never float.

**Relations** — a link from a detail page to another template is an FK. A category chip
that appears on many cards is a lookup table, not a string column. Repeated
comma-separated tags are a join table.

**Enums** — from filter options and category chips. If the UI offers exactly six sort
options, that is the domain.

**Indexes** — every filterable param, every sort key, and every FK. The UI tells you the
access patterns for free; that is the whole point of doing it in this order.

**Counts** — a `121` like-count on a card is a denormalized counter, not a `COUNT(*)` at
render time. Model both the counter column and the underlying table.

Write `03-structure/SCHEMA.md` — the reasoning, table by table, each field marked
`observed` or `inferred` — and `04-build/db/schema.sql` (or `schema.prisma`) as the
executable form. Never ship one without the other: the SQL alone hides which half you
made up.

### What you must not invent

Say "not derivable from the outside" and move on:

- Auth, sessions, permissions, roles — never guess at a security model
- Payment, payout, settlement, ledger tables
- Ranking, pricing, fraud, or recommendation logic. A feed order is an *observation*
  (`ORDER BY hot_score DESC`), not an algorithm you understood
- Anything you only saw once. One sample is not a pattern
- Internal IDs' meaning. `company=1` is a key; that it means "현대" is a guess unless the
  UI said so

## Seed data and the mock API

Seed from what recon already captured — the real copy on the real cards. That keeps the
clone honest and the layout truthful. Anything that looks like a real person gets
replaced with synthetic values first.

Keep the backend local and trivial: a single-file server reading SQLite or JSON, or
`json-server`. The deliverable is still one folder that runs offline. And when there is a
backend, `04-build/index.html` stops being self-contained — say so explicitly in the
handoff, because the base skill promises the opposite.

## Extra workspace

```
projects/<slug>/
  03-structure/ROUTES.md    route table, templates, in/out of scope
  03-structure/FLOWS.md     interactions: trigger → request → response → UI
  03-structure/SCHEMA.md    entities, fields, relations — observed vs inferred
  04-build/<route>/         one folder per cloned route
  04-build/db/              schema.sql, seed.sql, the mock server
  06-model/                 raw network captures backing the inference
```

## Report it honestly

At handoff, split the report in three: **동작함** (built and verified), **관찰됨**
(seen in traffic, reproduced approximately), **추론임** (designed from evidence, never
confirmed). The schema is almost entirely the third. A user who ships an inferred schema
believing it was observed has been misled by the report, not by the site.
