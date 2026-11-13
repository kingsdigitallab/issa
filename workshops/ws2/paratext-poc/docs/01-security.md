<!-- Written by chavezheras, drafted with OpenCode (GLM-5.3, served through ARC: https://docs.er.kcl.ac.uk/CREATE/ai_hub/) -->
<!-- Security review written by opencode:e-research/arc:apex, 12 Nov 2026, on request:
     audited every file the feat--ws2-paratext-poc branch adds over main and recorded the findings. -->

# Security review — paratext PoC

- **Branch:** `feat--ws2-paratext-poc`, 8 commits ahead of `main`, head `91562bc` at review time.
- **Scope of the diff:** 36 files (~21k lines added) — the two converters (`../convert_ws2.py`,
  `../convert_records.py`), `../../make_ws2_data.py`, `../serve_ws2.py`, the two paratext plugins
  (`../issa_ws2/`, `../issa_segments/`), the patched review UI copy (`../ui/static/app.js`,
  `index.html`, vendored JS/CSS), the generated explainer page (`../../issa_ws2_nwfa.html`),
  `pyproject.toml`/`uv.lock`, tests, and the committed review artifacts.
- **Line numbers** below are as of `91562bc` and will drift.

## Threat model

A localhost, single-reviewer tool. The data it renders is **semi-trusted**: the NWFA catalogue,
annotator workbooks, and model (pipeline) output — none of it attacker-controlled in the WS2
setting, but the UI is a generic renderer that will happily display *any* packaged paratext
round (the file data is an unvalidated JSONL; hand-edited or third-party rounds are possible).
Findings are graded against that: "crafted packaged data" is the realistic injection path.

## Summary

No high-severity, branch-introduced issues. A handful of latent injection points in the generic
frontend, plus inherited posture from paratext upstream.

| ID | Severity | Where | What |
|---|---|---|---|
| M-1 | Medium | `app.js:348-350` | XSS via unescaped `s.images` → `href`/`src` |
| L-2 | Low | `app.js:1733` | `escapeHtml` in wrong context (JS-string-in-attribute) in stats-row `onclick` |
| L-3 | Low | `app.js:713-727`, `1110`, `2318`, `2242`, `1905`, `683` | unescaped (today type-safe) attribute interpolations |
| L-4 | Low | `app.js:574-589` | no URL-scheme check on media links (`javascript:` survives escaping) |
| I-1 | Inherited | upstream `review/server.py` | no auth / Origin check; JSON parsed regardless of content-type |
| I-2 | Inherited | `pyproject.toml:8` + `uv.lock` | git dependency tracks a *mutable branch* (locked to a commit, though) |
| H-1 | Hygiene | `issa_ws2_nwfa.html:7` | CDN script (Chart.js) version-pinned but no SRI |
| H-2 | Hygiene | `ui/static/vendor/` | vendored hls.js/Oat files without recorded version/hash |

## Findings

### M-1 · XSS via unescaped `s.images` — app.js:348-350

```js
return `<div class="${variant}">${s.images
    .map((p) => `<a href="${p}" target="_blank"><img src="${p}" alt="page" /></a>`)
```

Record data goes into `href`/`src` raw. A packaged round with `images: ['"><img src=x onerror=…>']`
breaks out of either attribute — script injection. Not reachable with WS2's own data (the
`s.media?.src` branch short-circuits, so we never take this path), but this UI copy serves any
paratext project (issa-segments today, others later). **Fix:** `escapeHtml(p)` (plus an http(s)
scheme check, and `rel="noopener"` on the link — modern browsers imply noopener for
`target="_blank"`, but it costs nothing to say it).

### L-2 · Wrong-context escaping — app.js:1733

```js
<tr class="row-link" onclick="location.hash='#/eval/${escapeHtml(r.sample_id)}'">
```

HTML-escaping does not survive the attribute→JS boundary: `&#39;` is decoded back to `'` by the
HTML parser *before* the JS engine parses the `onclick` attribute, so an apostrophe in a
`sample_id` escapes the JS string → arbitrary JS. Safe today only because converter ids are
regex-constrained (`NWFA \d+|N_\d+`). Latent in the generic renderer. **Fix:** a `data-*`
attribute + delegated click listener (the pattern already used for seek buttons), or
`encodeURIComponent`.

### L-3 · Unescaped, currently type-safe attribute interpolations

`data-seek="${p.start}"`, `data-ostart="${g.start}"`, `data-oend="${…}"` (outlineHtml,
`app.js:713-727`), number-field `value="${value ?? ""}"` (`app.js:1110`),
`<progress value/max="${j.done}/${j.total}">` (`app.js:2318`), `ws-cards` max/value
(`app.js:2242`), `<span class="n">${scopes[sc]}</span>` (`app.js:1905`),
`st-${r.status}` / `k-${kind}` class fragments (`app.js:683`, `713`). All are ints/floats from
the packer or the upstream server today; a hand-edited `records_ws2.jsonl` or a third-party
round could break out of an attribute. **Fix (cheap, mechanical):** pass every interpolation
through `escapeHtml` (the file's own helper, `app.js:940-952`), or add a CSP `<meta>` tag to
make the class of bug inert.

### L-4 · No scheme allowlist on media URLs — app.js:574-589

The "Open it directly" link HTML-escapes `m.src` but `javascript:` passes escaping untouched;
crafted value ⇒ script execution on click. Same crafted-data class as above. **Fix:** only emit
the link for `http(s):`/relative URLs.

### I-1 · Inherited (upstream paratext): unauthenticated localhost API

The review server binds `127.0.0.1` by default (upstream `paratext/review/server.py:883`) and
`serve_ws2.py` only repoints `STATIC_DIR` at our copy — no branch change to exposure. But:
no authentication, no Origin/Host validation, and the POST/DELETE handlers
(`server.py:358-388`) JSON-parse bodies without checking `content-type`. Since
`text/plain` bodies are "simple requests" (no CORS preflight), any website open in the
reviewer's browser can fire silent POSTs/DELETEs against
`http://127.0.0.1:<port>/api/annotations|gold/…` and corrupt a running review session.
Standard localhost-tool posture — the default bind contains it to drive-by CSRF — but worth
fixing upstream (validate `Origin`/`Host`, require `application/json`) or only running the
server while a review is actually in progress.

Static serving is safe against traversal: `_serve_static` (`server.py:826-834`) resolves and
checks the target is under `STATIC_DIR`, and media `src` values (absolute paths) simply 404
there — no unbounded file route, so packaged `media.src` cannot be turned into local-file
disclosure.

### I-2 · Inherited: mutable git dependency

`pyproject.toml` pins `paratext-cli @ git+https://github.com/nls-lst/paratext.git@video-review` —
a *branch*, not a tag or commit. `uv.lock` resolves it to
`8d9671b131410a7b98d2f2b983eef8626f65f33e`, so installs are reproducible as locked, but a
`uv lock --upgrade` will silently pick up whatever the branch points at. Acceptable for a PoC —
just re-diff the package when re-locking.

### H-1 · CDN script without SRI — issa_ws2_nwfa.html:7

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
```

Version-pinned but no `integrity` attribute; a CDN compromise injects script into a public page.
The page already degrades gracefully when the script is blocked (`HAS_CHART`), so vendoring the
file or adding an SRI hash costs nothing and loses nothing.

### H-2 · Vendored files without provenance — ui/static/vendor/

`hls.light.min.mjs`, `oat.min.js`, `oat.min.css` are committed without a recorded upstream
version or hash (`ui/README.md` documents the copy's upstream *branch*, not these versions).
Record version + SHA somewhere (e.g. ui/README.md) so a future audit can re-verify them.

## Reviewed and clean

- **Converters:** `ffprobe` is the only subprocess, called argv-list form with a fixed binary —
  no shell, no injection (`convert_ws2.py:224-229`). The docx is opened by reading a single
  fixed member (`word/document2.xml`), never extracted — no zip-slip
  (`convert_ws2.py:197-214`). No network, no `eval`/`exec`, no secrets; output goes to stdout
  or `--out`. Malicious-xlsx memory-DoS is an accepted local-tool risk.
- **`serve_ws2.py` / plugins:** module-variable repoint plus declarative pydantic schemas;
  no new endpoints, handlers, or file writes.
- **Authored UI paths:** annotator notes, compare-grid values and overlap highlighting,
  outlines, diffs, export dialogs, workshop errors — all consistently `escapeHtml`ed; the
  semi-trusted annotator/model text renders safely.
- **HF OAuth (upstream copy):** PKCE + `state` check, token in `sessionStorage` only, sent as
  `Bearer` to same-origin endpoints, `postMessage` origin-checked (`app.js:1840`), storage-event
  handler same-origin by construction (`app.js:1841-1843`).
- **`index.html` pre-paint theme script:** `localStorage` value goes through
  `setAttribute`/style sinks only — no injection surface (`index.html:14-20`).
- **Repo hygiene:** no secrets in the committed review artifacts; per-reviewer
  `review/annotations.db` is gitignored (`.gitignore`); generated `records_ws2.jsonl` and the
  videos never enter git.

## Recommended actions

1. Small hardening patch to `app.js` (~30 lines, no behaviour change): escape `imagesHtml`,
   replace the stats-row `onclick` with a delegated `data-`-attribute handler, escape the
   numeric attribute interpolations, scheme-check media URLs. Verify with `uv run pytest -q`
   plus a browser smoke test.
2. Vendor Chart.js (or add SRI) in `issa_ws2_nwfa.html`; record versions/hashes of the vendored
   UI files in `ui/README.md`.
3. Raise the content-type/Origin validation gap with paratext upstream (I-1); until then, only
   run `serve_ws2.py` while a review is in progress.
