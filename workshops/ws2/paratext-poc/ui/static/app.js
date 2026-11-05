// paratext review UI. The pipeline emits a per-dataset
// view.json contract (GET /api/view) describing how to display and review a
// dataset: panels of fields (label + type), layout, scoring verdicts, and an
// optional flag control. This file renders generically from that contract and
// holds no per-schema knowledge.
// Keyboard: [f] flag (when a flag control exists), verdict hotkeys (1/2/3 by
//   default), [→] next, [←] previous, [Ctrl+s] save.

// ── Theme toggle ──────────────────────────────────────────────────────
// Oat sets `color-scheme: light dark`, so forcing colorScheme on the root
// switches every light-dark() token. Unset = follow the OS. The pre-paint
// script in index.html applies the stored value; this wires the button.
const themeToggle = document.getElementById("theme-toggle");
if (themeToggle) {
  const getTheme = () =>
    localStorage.getItem("theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");

  const applyTheme = (t) => {
    document.documentElement.style.colorScheme = t;
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("theme", t);
    themeToggle.textContent = t === "dark" ? "☀" : "☽";
  };

  applyTheme(getTheme());
  themeToggle.addEventListener("click", () => {
    applyTheme(getTheme() === "dark" ? "light" : "dark");
  });
}

const state = {
  datasets: [], // [{name, schema, count, base, round, active}]
  dataset: null, // current dataset name
  view: null, // the /api/view contract for state.viewDataset
  viewDataset: null, // which dataset state.view describes
  readOnly: false, // true when current dataset is an archived (non-active) round
  samples: [], // the working list: full list in review mode, filtered queue in eval mode
  allSamples: [], // unfiltered list (eval mode uses it for the header counts)
  samplesMode: null, // "review" | "eval" — so a mode switch reloads the working list
  index: 0,
  current: null,
  evalDirty: false, // an unsaved edit exists in the correction editor
  workshop: undefined, // undefined = not asked yet; false = not workshop mode
};

// Fetch (and cache) the display/review contract for the current dataset.
async function ensureView() {
  if (state.view && state.viewDataset === state.dataset) return;
  const res = await fetch(api("api/view"));
  state.view = await res.json();
  state.viewDataset = state.dataset;
}

function groupDatasets(datasets) {
  const byBase = new Map();
  for (const d of datasets) {
    const g = byBase.get(d.base) ?? { base: d.base, schema: d.schema, rounds: [] };
    g.rounds.push(d);
    byBase.set(d.base, g);
  }
  for (const g of byBase.values()) {
    g.rounds.sort((a, b) => b.round - a.round);
    g.active = g.rounds[0];
    g.archived = g.rounds.slice(1);
  }
  return Array.from(byBase.values()).sort((a, b) => a.base.localeCompare(b.base));
}

function api(path, params = {}) {
  // Use a relative path so this works whether the app is served at the root
  // or behind a reverse-proxy prefix (e.g. /verify/). Building via `new URL`
  // with location.origin would strip that prefix.
  const qs = new URLSearchParams();
  if (state.dataset) qs.set("dataset", state.dataset);
  for (const [k, v] of Object.entries(params)) qs.set(k, v);
  const q = qs.toString();
  return q ? `${path}?${q}` : path;
}

async function loadDatasets() {
  const res = await fetch("api/datasets");
  state.datasets = await res.json();
}

function setDataset(name) {
  const d = state.datasets.find((d) => d.name === name);
  if (!d) {
    state.dataset = null;
    state.readOnly = false;
  } else {
    state.dataset = d.name;
    state.readOnly = d.active === false;
  }
  state.view = null;
  state.viewDataset = null;
  state.samples = [];
  state.allSamples = [];
  state.samplesMode = null;
  state.index = 0;
  state.current = null;
}

async function loadList(targetId = null) {
  const res = await fetch(api("api/samples"));
  state.samples = await res.json();
  state.samplesMode = "review";
  if (!state.samples.length) {
    document.getElementById("progress").textContent = "";
    document.getElementById("view").innerHTML = `
      <h2>${escapeHtml(state.view?.title ?? "Review")}</h2>
      <p class="text-light">Nothing to review in this dataset — every record was filtered
        out during packaging (e.g. blank versos). Try another round from the picker.</p>
      <p><a href="#/select" class="button outline small">← Back to datasets</a></p>`;
    return;
  }
  if (targetId !== null) {
    const idx = state.samples.findIndex((s) => String(s.id) === String(targetId));
    if (idx !== -1) {
      state.index = idx;
      await loadSample();
      return;
    }
  }
  const firstUnannotated = state.samples.findIndex((s) => !s.annotated);
  state.index = firstUnannotated === -1 ? 0 : firstUnannotated;
  await loadSample();
}

async function loadSample() {
  const id = state.samples[state.index].id;
  const res = await fetch(api(`api/samples/${id}`));
  state.current = await res.json();
  clearTimeout(state.evalTimer);
  state.evalDirty = false;
  if (isEval()) renderEditor();
  else render();
}

function fmt(v) {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "yes" : "no";
  const scalar = (x) =>
    x !== null && typeof x === "object" ? JSON.stringify(x) : String(x);
  if (Array.isArray(v)) return v.length ? v.map(scalar).join(", ") : "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

// A <details> the reviewer opens on demand; omitted entirely when empty.
function collapsedBlock(obj, f) {
  const v = obj?.[f.key];
  if (v === null || v === undefined || v === "") return "";
  return `
    <details class="field-collapsed" style="margin:.5rem 0;">
      <summary>${escapeHtml(f.label)}</summary>
      <div style="margin:.4rem 0 .2rem .5rem; white-space:pre-wrap;">${escapeHtml(fmt(v))}</div>
    </details>`;
}

// Render a panel's body: scalar fields as a key/value table (row-header th +
// value td, styled by Oat), then any "entries" fields as their own columnar
// tables, then any collapsed fields.
function panelBody(obj, fields) {
  const shown = fields.filter((f) => !f.collapsed);
  const scalar = shown.filter((f) => f.type !== "entries");
  const entries = shown.filter((f) => f.type === "entries");
  const rows = scalar
    .map(
      (f) =>
        `<tr><th scope="row">${escapeHtml(f.label)}</th><td>${escapeHtml(fmt(obj?.[f.key]))}</td></tr>`,
    )
    .join("");
  return `
    ${scalar.length ? `<div class="table"><table><tbody>${rows}</tbody></table></div>` : ""}
    ${entries.map((f) => entriesBlock(f, obj?.[f.key])).join("")}
    ${fields.filter((f) => f.collapsed).map((f) => collapsedBlock(obj, f)).join("")}`;
}

// The read-only entries table body (shared by the display panels and the eval
// editor's read-only rounds). Columns = item fields, one row per entry.
function entriesTable(items, entries) {
  const head = items.map((it) => `<th>${escapeHtml(it.label)}</th>`).join("");
  const body = entries
    .map(
      (e) => `<tr>${items.map((it) => `<td>${escapeHtml(fmt(e[it.key]))}</td>`).join("")}</tr>`,
    )
    .join("");
  return `<div class="table"><table class="entry-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function entryItems(field, entries) {
  return field.item_fields ?? Object.keys(entries[0] ?? {}).map((k) => ({ key: k, label: k }));
}

// Entries are genuinely tabular, so render them as an Oat table.
function entriesBlock(field, entries) {
  if (!Array.isArray(entries) || !entries.length) {
    return `<p><em>No ${escapeHtml(field.label.toLowerCase())}.</em></p>`;
  }
  return `
    <h4>${escapeHtml(field.label)} (${entries.length})</h4>
    ${entriesTable(entryItems(field, entries), entries)}`;
}

// The sticky nav overlaps anything else sticky, and it wraps, so its height is
// measured rather than assumed.
function trackNavHeight() {
  const nav = document.querySelector("nav[data-topnav]");
  if (!nav) return;
  const set = () =>
    document.documentElement.style.setProperty("--nav-h", `${nav.offsetHeight}px`);
  set();
  if (window.ResizeObserver) new window.ResizeObserver(set).observe(nav);
  else window.addEventListener("resize", set);
}

function renderHeader() {
  const nav = document.querySelector("nav[data-topnav]");
  if (!nav) return;

  // Gate Review/Results until a dataset is chosen — with no selection they just
  // fall back to the picker (looking like dead buttons).
  const gated = state.dataset ? "" : "none";
  for (const id of ["nav-review", "nav-stats"]) {
    const el = document.getElementById(id);
    if (el) el.style.display = gated;
  }

  // A project + round picker in the nav, so you can switch datasets without
  // returning to the homepage. Shown whenever there's more than one to pick.
  let host = document.getElementById("dataset-picker-host");
  if (!host) {
    host = document.createElement("span");
    host.id = "dataset-picker-host";
    nav.insertBefore(host, document.getElementById("progress"));
  }
  if (state.datasets.length <= 1) {
    host.innerHTML = "";
    return;
  }

  // Oat popover dropdown (ot-dropdown): a trigger button + a <menu popover>.
  // Menu items carry popovertargetaction="hide" so a click closes the popover
  // natively; the change listener handles selection.
  const MENU_ID = "nav-dataset-menu";
  const groups = groupDatasets(state.datasets);
  const roundLabel = (d) => `round ${d.round}${d.active === false ? " (archived)" : ""}`;
  const item = (d, label) =>
    `<button role="menuitem" class="ghost" data-dataset="${escapeHtml(d.name)}"
       popovertarget="${MENU_ID}" popovertargetaction="hide"
       style="display:block; width:100%; text-align:left;${
         d.name === state.dataset ? " font-weight:600;" : ""
       }">${d.name === state.dataset ? "✓ " : ""}${escapeHtml(label)}</button>`;

  const menuInner = groups
    .map((g, gi) => {
      const sep = gi > 0 ? "<hr>" : "";
      if (g.rounds.length === 1) return sep + item(g.rounds[0], g.base);
      const header = `<small role="presentation" style="display:block;
        padding:.25rem .75rem; color:var(--muted-foreground);">${escapeHtml(g.base)}</small>`;
      return sep + header + g.rounds.map((d) => item(d, roundLabel(d))).join("");
    })
    .join("");

  // Label the trigger with the current selection (or a prompt to choose).
  let triggerLabel = "Choose a project…";
  if (state.dataset) {
    const g = groups.find((g) => g.rounds.some((d) => d.name === state.dataset));
    const d = g?.rounds.find((d) => d.name === state.dataset);
    if (g && d) triggerLabel = g.rounds.length === 1 ? g.base : `${g.base} · ${roundLabel(d)}`;
  }

  host.innerHTML = `
    <ot-dropdown style="margin-left:.5rem;">
      <button popovertarget="${MENU_ID}" class="outline small"
              style="display:inline-flex; align-items:center; gap:.35rem;">
        ${escapeHtml(triggerLabel)}
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>
      </button>
      <menu popover id="${MENU_ID}">${menuInner}</menu>
    </ot-dropdown>`;

  host.querySelectorAll("[data-dataset]").forEach((btn) => {
    btn.addEventListener("click", () => {
      setDataset(btn.dataset.dataset);
      if (currentRoute() === "select") location.hash = "#/review";
      route();
    });
  });
}

function renderPicker() {
  document.getElementById("progress").textContent = "";
  if (!state.datasets.length) {
    document.getElementById("view").innerHTML =
      `<p>No datasets found. Run <code>paratext run -p &lt;project&gt;</code> to create a
         review round under <code>review/</code>, then reload — or point
         <code>paratext review</code> at a directory that contains one.</p>
    <p class="page-foot">
      <code>paratext inspect</code> shows the fields, prompt and source options
      each installed project runs with.
    </p>`;
    return;
  }

  // One card per project, showing the round you would actually review. Earlier
  // rounds are history of a dataset, not a different dataset, so they are
  // reached from Results rather than nested here.
  const cards = groupDatasets(state.datasets)
    .map((g) => {
      const a = g.active;
      const earlier = g.rounds.length - 1;
      return `<article class="card mb-2">
        <h3>${escapeHtml(g.base)}</h3>
        <p class="text-light">
          ${g.schema && g.schema !== g.base
            ? `<span class="badge outline">${escapeHtml(g.schema)}</span>`
            : ""}
          <span class="badge outline">round ${a.round}</span>
          ${a.count} sample${a.count === 1 ? "" : "s"}${
            earlier ? ` · ${earlier} earlier round${earlier === 1 ? "" : "s"}` : ""
          }
        </p>
        <button class="button primary" data-dataset="${escapeHtml(a.name)}">Review →</button>
      </article>`;
    })
    .join("");

  document.getElementById("view").innerHTML = `
    <h2>Choose a dataset to review</h2>
    <div style="max-width:32rem;">${cards}</div>
  `;
  document.querySelectorAll("[data-dataset]").forEach((btn) => {
    btn.addEventListener("click", () => {
      setDataset(btn.dataset.dataset);
      location.hash = "#/review";
      route();
    });
  });
}

// variant "thumbs" → small inline gallery (stacked layout); "media" → large
// images sized to their column (split layout).
function imagesHtml(s, variant) {
  if (s.media?.src) return mediaHtml(s.media, s);
  return `<div class="${variant}">${s.images
    .map((p) => `<a href="${p}" target="_blank"><img src="${p}" alt="page" /></a>`)
    .join("")}</div>`;
}

// ── ISSA WS2 changes (see ui/README.md): track grouping, collection bar, ───
// ── separators, now-playing highlight ──────────────────────────────────────
// Track names may carry a group prefix: "pipe:" (pipeline), "human:" (annotator
// consensus), "ann:" (per-annotator breakdown, folded away by default).
function trackInfo(t) {
  const m = /^(pipe|human|ann):\s*/.exec(t.name ?? "");
  return { group: m ? m[1] : "other", label: (t.name ?? "").replace(/^(pipe|human|ann):\s*/, "") };
}

// Item text may start with "@kind " (sep | agreed | contested).
function itemKind(it) {
  const m = /^@(\w+) ([\s\S]*)$/.exec(it.text ?? "");
  return m ? { kind: m[1], text: m[2] } : { kind: "", text: it.text ?? "" };
}

function collectionClass(name) {
  return /channel m/i.test(name) ? "coll-chm" : /film/i.test(name) ? "coll-fv" : "coll-other";
}

// [← Previous] [collection · file · duration] [Next →], shown under the video
// and again at the bottom of the page.
function collectionBar(s) {
  const g = s.ground_truth ?? {};
  if (!g.collection) return "";
  const first = state.index === 0;
  const last = state.index === state.samples.length - 1;
  const next = last
    ? `<a href="#/stats" class="button primary">Done — results →</a>`
    : `<button type="button" class="primary" data-nav="1">Next →</button>`;
  return `<div class="collection-bar ${collectionClass(g.collection)}">
      <button type="button" data-nav="-1"${first ? " disabled" : ""}>← Previous</button>
      <div class="coll-info"><strong>${escapeHtml(g.collection)}</strong>
        <span>${escapeHtml(g.filename ?? "")}${g.file_duration ? ` · ${escapeHtml(g.file_duration)}` : ""}</span></div>
      ${next}
    </div>`;
}

// A sample with `media` shows a player instead of images. `media.tracks` adds
// one timeline strip per source; paratext.media documents the shape.
function mediaHtml(m, s) {
  const poster = m.poster ? ` poster="${escapeHtml(m.poster)}"` : "";
  const error = `<div role="alert" data-variant="danger" id="media-error" hidden></div>`;
  if (m.end == null)
    return `<div class="media-player"><video id="media" controls preload="metadata"${poster}></video>${error}</div>`;
  const tracks = m.tracks?.length ? m.tracks : [{ name: "", items: [] }];
  const row = (t, i) => {
    const { group, label } = trackInfo(t);
    return `<div class="media-track grp-${group}">
        <div class="media-track-name" title="${escapeHtml(t.note ?? "")}">${escapeHtml(label)}${t.note ? " ≈" : ""}</div>
        <div class="media-range" data-track="${i}">
          <div class="media-range-prog"></div><div class="media-range-head"></div>
        </div>
      </div>`;
  };
  // Only the pipeline tracks stay in view; every human track (consensus and
  // per-annotator) sits in the collapsed breakdown beneath them.
  const isHuman = (t) => ["human", "ann"].includes(trackInfo(t).group);
  const main = tracks.map((t, i) => [t, i]).filter(([t]) => !isHuman(t));
  const brk = tracks.map((t, i) => [t, i]).filter(([t]) => isHuman(t));
  const rows =
    main.map(([t, i]) => row(t, i)).join("") +
    (brk.length
      ? `<details class="ann-breakdown"><summary>Human annotation (${brk.length} tracks)</summary>${brk
          .map(([t, i]) => row(t, i))
          .join("")}</details>`
      : "");
  const approx = tracks
    .filter((t) => t.note)
    .map((t) => ` · ≈ ${escapeHtml(t.name)}: ${escapeHtml(t.note)}`)
    .join("");
  const legend = tracks.some((t) => (t.items ?? []).some((it) => itemKind(it).kind))
    ? `<span class="legend"><i class="k-sep"></i>separator <i class="k-agreed"></i>annotators agree <i class="k-contested"></i>contested</span>`
    : "";
  return `<div class="media-player"><video id="media" controls preload="metadata"${poster}></video>${error}
    ${s ? collectionBar(s) : ""}
    <div class="media-timeline" id="media-timeline">${rows}</div>
    <p class="media-range-label"><span id="media-range-label"></span>${approx} ${legend}</p></div>`;
}

function clock(t) {
  t = Math.max(0, Math.round(t));
  const h = Math.floor(t / 3600);
  const mm = String(Math.floor((t % 3600) / 60)).padStart(2, "0");
  const ss = String(t % 60).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

// Whole-tape strips: the clip's start–end highlighted, each track's segments as
// blocks, a playhead. Video handlers are on* properties so a carried-over video
// isn't given a second set of listeners on every re-render. The hover label is
// our own element, not Oat's tooltip: shotlist text is long and needs wrapping
// and clamping to the timeline's edges.
// ISSA WS2: items without an `end` run to the next item's start (so a segment
// highlights its own span), "@kind" prefixes are styled, the item under the
// playhead is highlighted, and the programme/segment outlines follow playback.
function bindTimeline(video, s) {
  const timeline = document.getElementById("media-timeline");
  const label = document.getElementById("media-range-label");
  if (!timeline) return;
  const { start = 0, end } = s.media;
  const tracks = s.media.tracks?.length ? s.media.tracks : [{ items: [] }];
  const items = tracks.map((t) =>
    (t.items ?? []).map((it, k, arr) => ({
      ...it,
      ...itemKind(it),
      hasEnd: it.end != null,
      e: it.end ?? arr[k + 1]?.start ?? end,
    })),
  );
  const rows = [...timeline.querySelectorAll(".media-range")];
  const tip = document.createElement("div");
  tip.className = "media-tip";
  tip.style.display = "none";
  timeline.append(tip);
  const trackOf = (row) => +row.dataset.track;
  const at = (list, t) => list.findLastIndex((it) => it.start <= t && t < it.e);

  const draw = () => {
    const dur = video.duration;
    if (!timeline.isConnected || !Number.isFinite(dur) || dur <= 0) return;
    const pct = (t) => `${Math.min(100, (t / dur) * 100)}%`;
    const t = video.currentTime;
    rows.forEach((row) => {
      const list = items[trackOf(row)];
      const prog = row.querySelector(".media-range-prog");
      // The clip window only means something when it is a part of the file.
      prog.style.display = start <= 0 && end >= dur - 1 ? "none" : "";
      prog.style.left = pct(start);
      prog.style.width = `calc(${pct(end - start)} + 2px)`;
      row.querySelector(".media-range-head").style.left = pct(t);
      if (!row.dataset.built) {
        row.dataset.built = "1";
        row._segs = list.map((it) => {
          const seg = document.createElement("div");
          seg.className = `media-seg${it.hasEnd ? " block" : ""}${it.kind ? ` kind-${it.kind}` : ""}`;
          seg.style.left = pct(it.start);
          seg.style.width = pct(it.e - it.start);
          row.append(seg);
          return seg;
        });
      }
      const now = at(list, t);
      if (row._now !== now) {
        row._segs.forEach((el, j) => el.classList.toggle("playing", j === now));
        row._now = now;
      }
    });
    document.querySelectorAll("[data-ostart]").forEach((el) => {
      el.classList.toggle("playing", +el.dataset.ostart <= t && t < +el.dataset.oend);
    });
    label.textContent =
      `${s.media.label ?? "Clip"} ${clock(start)}–${clock(end)} (${clock(end - start)}) of ${clock(dur)} · now ${clock(t)}`;
  };

  const itemAt = (row, e) => {
    const r = row.getBoundingClientRect();
    const t = ((e.clientX - r.left) / r.width) * video.duration;
    const list = items[trackOf(row)];
    const i = at(list, t);
    return { t, i, item: list[i] };
  };

  rows.forEach((row) => {
    const segs = () => row._segs ?? [];
    row.onmousemove = (e) => {
      if (!Number.isFinite(video.duration)) return;
      const { t, i, item } = itemAt(row, e);
      segs().forEach((el, j) => el.classList.toggle("active", j === i));
      const text = item
        ? `${clock(item.start)}–${clock(item.e)} · ${item.text.length > 320 ? item.text.slice(0, 317) + "…" : item.text}`
        : clock(t);
      tip.textContent = text;
      tip.style.display = "block";
      const box = timeline.getBoundingClientRect();
      const x = e.clientX - box.left - tip.offsetWidth / 2;
      tip.style.left = `${Math.max(0, Math.min(x, box.width - tip.offsetWidth))}px`;
      tip.style.top = `${row.offsetTop - tip.offsetHeight - 6}px`;
    };
    row.onmouseleave = () => {
      tip.style.display = "none";
      segs().forEach((el) => el.classList.remove("active"));
    };
    // A click on a segment plays it from its start; elsewhere, seek to the spot.
    row.onclick = (e) => {
      if (!Number.isFinite(video.duration)) return;
      const { t, item } = itemAt(row, e);
      video.currentTime = item ? item.start : t;
    };
  });

  video.ontimeupdate = draw;
  video.onloadedmetadata = draw;
  video.ondurationchange = draw;
  draw();
}

let hlsPlayer = null;

// render() rebuilds the view on every verdict click; carry a playing video over
// rather than reloading it.
function keepMedia(s, previous) {
  const fresh = document.getElementById("media");
  if (!fresh || !s.media?.src) return;
  if (previous && previous.dataset.sid === String(s.id)) {
    fresh.replaceWith(previous);
  } else {
    if (previous) {
      previous.removeAttribute("src");
      previous.load();
    }
    fresh.dataset.sid = String(s.id);
    attachMedia(s.media, fresh);
  }
  const video = document.getElementById("media");
  bindSeek(video, s.media.start ?? 0);
  bindTimeline(video, s);
}

// The player only says that it failed; one fetch of the source says why: a
// missing file, a server that blocks playback from here (CORS), or, when the
// fetch succeeds, a format or codec this browser can't play.
async function mediaError(m, reason) {
  const el = document.getElementById("media-error");
  if (!el || !el.hidden) return;
  el.hidden = false;
  el.textContent = "This video couldn't be played…";
  document.getElementById("media-timeline")?.setAttribute("hidden", "");
  let why = reason;
  try {
    const res = await fetch(m.src, { method: "GET", headers: { range: "bytes=0-0" } });
    if (!res.ok) why = `HTTP ${res.status}: the file isn't there`;
  } catch {
    why = "its server can't be reached, or doesn't allow playback from this site (CORS)";
  }
  el.innerHTML = `This video couldn't be played: ${escapeHtml(why)}.
    <a href="${escapeHtml(m.src)}" target="_blank" rel="noopener">Open it directly</a>`;
}

async function attachMedia(m, video) {
  hlsPlayer?.destroy();
  hlsPlayer = null;
  const start = m.start ?? 0;
  const isHls = m.type === "hls" || /\.m3u8(\?|$)/.test(m.src);
  video.addEventListener("error", () => {
    if (!video.isConnected) return; // a player being torn down between samples
    const codes = { 2: "a network error", 3: "it can't be decoded", 4: "this browser can't play its format" };
    mediaError(m, codes[video.error?.code] ?? "an unknown error");
  });
  if (isHls && !video.canPlayType("application/vnd.apple.mpegurl")) {
    const { default: Hls } = await import("./vendor/hls.light.min.mjs");
    hlsPlayer = new Hls({ startPosition: start });
    hlsPlayer.on(Hls.Events.ERROR, (_, d) => {
      if (d.fatal) mediaError(m, d.details);
    });
    hlsPlayer.loadSource(m.src);
    hlsPlayer.attachMedia(video);
  } else {
    video.src = m.src;
    video.addEventListener("loadedmetadata", () => (video.currentTime = start), { once: true });
  }
  if (m.end) {
    video.addEventListener("timeupdate", () => {
      if (video.currentTime >= m.end && !video.dataset.pastEnd) {
        video.dataset.pastEnd = "1";
        video.pause();
      }
    });
    video.addEventListener("seeked", () => {
      video.dataset.pastEnd = video.currentTime >= m.end ? "1" : "";
    });
  }
}

// Timecodes in entries tables seek, relative to the clip start.
function bindSeek(video, start) {
  document.querySelectorAll(".entry-table td").forEach((td) => {
    const tc = td.textContent.trim().match(/^(?:(\d+):)?(\d{1,2}):(\d{2})$/);
    if (!tc) return;
    td.classList.add("seek");
    td.title = "Play from here";
    td.addEventListener("click", () => {
      video.currentTime = start + (+tc[1] || 0) * 3600 + +tc[2] * 60 + +tc[3];
      video.play();
    });
  });
}

// ── ISSA WS2: existing-vs-predicted comparison, outlines, notes + scoring ───
const STATUS = {
  match: ["✓", "Same"],
  close: ["≈", "Close"],
  differs: ["≠", "Differs"],
  added: ["＋", "Added by the pipeline"],
  missing: ["∅", "Not produced by the pipeline"],
  none: ["", "Neither side has a value"],
  text: ["", "Free text: compared by shared words, not scored"],
};

const STOP = new Set(
  "about after also and are but for from had has have her him his into its not that the their them then there these they this was were which while with who will would been being over than onto upon what when where".split(" "),
);
// Lower-cased content words: 4+ letters or any number, light plural stripping.
function factWords(text) {
  const out = new Map();
  for (const w of (text ?? "").toLowerCase().match(/[\p{L}\p{N}]+/gu) ?? []) {
    if (/^p\d+$/.test(w) || STOP.has(w)) continue;
    if (!/\d/.test(w) && w.length < 4) continue;
    out.set(w.replace(/(?<=\p{L}{3})s$/u, ""), true);
  }
  return out;
}
// Wrap words that occur on both sides in <mark>; returns [leftHtml, rightHtml].
function overlapHtml(a, b) {
  const wa = factWords(a);
  const wb = factWords(b);
  const paint = (text, other) =>
    escapeHtml(text).replace(/[\p{L}\p{N}]+/gu, (w) =>
      other.has(w.toLowerCase().replace(/(?<=\p{L}{3})s$/u, "")) && factWords(w).size ? `<mark>${w}</mark>` : w,
    );
  return [paint(a, wb), paint(b, wa)];
}

function cmpValue(v, html) {
  return v ? `<div class="cmp-val">${html ?? escapeHtml(v)}</div>` : `<div class="cmp-val empty">—</div>`;
}

function compareHtml(s) {
  const m = s.model_output;
  const row = (r) => {
    const [lh, rh] = r.status === "text" ? overlapHtml(r.left, r.right) : [undefined, undefined];
    return `<div class="cmp-row st-${r.status}">
      <div class="cmp-cell cmp-ex"><span class="cmp-k">${escapeHtml(r.left_label)}</span>${cmpValue(r.left, lh)}</div>
      <div class="cmp-st" title="${STATUS[r.status]?.[1] ?? ""}">${STATUS[r.status]?.[0] ?? ""}</div>
      <div class="cmp-cell cmp-pr"><span class="cmp-k">${escapeHtml(r.right_label)}</span>${cmpValue(r.right, rh)}</div>
    </div>`;
  };
  const extras = (m.extras ?? [])
    .map((e) =>
      row({ left_label: e.label, left: null, right_label: e.label, right: e.right, status: "added" }),
    )
    .join("");
  return `<section class="compare">
      <div class="cmp-head">
        <div class="cmp-ex"><h3>Archive record</h3><small>before processing</small></div><div></div>
        <div class="cmp-pr"><h3>ISSA pipeline</h3><small>after processing</small></div>
      </div>
      ${(m.compare ?? []).map(row).join("")}
      ${extras ? `<div class="cmp-sub">Also produced by the pipeline</div>${extras}` : ""}
      <p class="cmp-key">${Object.entries(STATUS)
        .filter(([k]) => k !== "none" && k !== "text")
        .map(([k, [icon, text]]) => `<span class="st-${k}"><b>${icon}</b> ${text}</span>`)
        .join(" ")} · indicative rules, not a score · <mark>highlighted</mark> = words in both texts</p>
    </section>`;
}

function outlineHtml(items, empty) {
  if (!items?.length) return `<p class="outline-empty">${escapeHtml(empty)}</p>`;
  return items
    .map((p, i) => {
      const segs = p.segments ?? [];
      const chip = p.kind ? `<span class="chip k-${p.kind}">${p.support ?? ""}</span>` : "";
      const head = `<button type="button" class="seek" data-seek="${p.start}" title="Play from ${clock(p.start)}">▶</button>
        <span class="o-time">${clock(p.start)}–${clock(p.end)}</span>
        <span class="o-title">P${i + 1} · ${escapeHtml(p.summary || "(no description)")}</span>${chip}
        <span class="o-count">${segs.length ? `${segs.length} seg` : ""}</span>`;
      const segRows = segs
        .map((g, k) => {
          const e = segs[k + 1]?.start ?? p.end;
          return `<div class="outline-seg${g.kind ? ` k-${g.kind}` : ""}" data-ostart="${g.start}" data-oend="${e}">
              <button type="button" class="seek" data-seek="${g.start}" title="Play from ${clock(g.start)}">▶</button>
              <span class="o-time">${clock(g.start)}</span><span class="o-title">${escapeHtml(g.text)}</span></div>`;
        })
        .join("");
      return segs.length
        ? `<details class="outline-prog" data-ostart="${p.start}" data-oend="${p.end}"><summary>${head}</summary>${segRows}</details>`
        : `<div class="outline-prog flat" data-ostart="${p.start}" data-oend="${p.end}"><div class="flat-head">${head}</div></div>`;
    })
    .join("");
}

function outlinesHtml(s) {
  return `<section class="outlines">
      <div class="outline-tools"><h3>Programmes and segments</h3>
        <button type="button" class="outline small" data-outline="expand">Expand all</button>
        <button type="button" class="outline small" data-outline="collapse">Collapse all</button></div>
      <div class="outline-cols">
        <div class="cmp-ex"><h4>Human annotators${s.ground_truth.agreement ? ` <small>${escapeHtml(s.ground_truth.agreement)}</small>` : ""}</h4>
          ${outlineHtml(s.ground_truth.outline, "No human annotation loaded for this video yet.")}</div>
        <div class="cmp-pr"><h4>ISSA pipeline</h4>${outlineHtml(s.model_output.outline, "No programmes predicted.")}</div>
      </div>
    </section>`;
}

// Annotator notes (no pipeline counterpart) sit beside the scoring they inform.
function scoreRowHtml(s, a) {
  const notes = s.ground_truth.annotator_notes ?? [];
  return `<section class="score-row">
      <div class="cmp-ex"><h4>Annotator notes</h4>${
        notes.length
          ? `<ul>${notes.map((n) => `<li>${escapeHtml(n)}</li>`).join("")}</ul>`
          : `<p class="outline-empty">No annotator notes yet.</p>`
      }</div>
      <div class="cmp-pr"><h4>Your verdict on the pipeline</h4>${scoringButtons(a)}${notesForm(a)}</div>
    </section>`;
}

function compareBody(s, a) {
  return `<section>${imagesHtml(s, "thumbs")}</section>
    ${outlinesHtml(s)}${compareHtml(s)}${scoreRowHtml(s, a)}${collectionBar(s)}`;
}

// Seek buttons and the expand/collapse tools live inside #view, which render()
// rebuilds, so one delegated listener on the stable parent handles them.
document.getElementById("view")?.addEventListener("click", (e) => {
  const seek = e.target.closest("[data-seek]");
  if (seek) {
    e.preventDefault();
    e.stopPropagation();
    const video = document.getElementById("media");
    if (!video) return;
    video.currentTime = +seek.dataset.seek;
    video.play?.().catch(() => {});
    const top = video.getBoundingClientRect().top;
    const navH = document.querySelector("nav[data-topnav]")?.offsetHeight ?? 0;
    if (top < navH) video.scrollIntoView({ block: "start", behavior: "smooth" });
    return;
  }
  const tool = e.target.closest("[data-outline]");
  if (tool)
    document
      .querySelectorAll("details.outline-prog")
      .forEach((d) => (d.open = tool.dataset.outline === "expand"));
});

function render() {
  const s = state.current;
  const a = s.annotation ?? {};
  const view = state.view;
  const remaining = state.samples.filter((x) => !x.annotated).length;
  document.getElementById("progress").innerHTML = `
    <span class="sample-label" title="${escapeHtml(String(s.document_id ?? s.id))}"
      >Sample ${state.index + 1} / ${state.samples.length} —
      ${escapeHtml(String(s.document_id ?? s.id))}</span>
    <button id="jump-next" class="outline small"
            ${remaining === 0 ? "disabled" : ""}>
      Next unchecked${remaining ? ` (${remaining})` : ""}
    </button>
  `;
  document.getElementById("jump-next")?.addEventListener("click", jumpToNextUnchecked);

  const detScore = s.deterministic_scores?.accuracy;
  const detBadge =
    detScore !== undefined
      ? `<p class="progress">Deterministic score: ${(detScore * 100).toFixed(0)}% — ${
          escapeHtml(s.deterministic_explanation ?? "")
        }</p>`
      : "";

  const panelsHtml = view.panels.map((p) => renderPanel(p, s, a)).join("");
  const heading = `<h2>${escapeHtml(view.title)} ${escapeHtml(String(s.document_id ?? s.id))}</h2>`;
  const atFirst = state.index === 0;
  const atLast = state.index === state.samples.length - 1;
  // At the end of the pass the primary CTA becomes a route to the stats summary,
  // rather than a Next button that silently no-ops.
  const nextControl = atLast
    ? `<a href="#/stats" class="button primary">Done — see results →</a>`
    : `<button id="next" class="primary">Next →</button>`;
  const nav = `
    <div class="controls">
      <button id="prev"${atFirst ? " disabled" : ""}>← Previous</button>
      ${nextControl}
    </div>`;
  const readOnlyBanner = state.readOnly
    ? `<aside class="readonly-banner">
        This round is archived (read-only). Existing annotations are shown but cannot be changed.
        <a href="#/select">Switch round →</a>
      </aside>`
    : "";

  // Split layout: image beside the (single) model panel, nothing to scroll
  // past before scoring. Stacked: image on top, then the compare panes.
  const compareMode = !!(s.model_output?.compare && s.media?.src);
  const body = compareMode
    ? compareBody(s, a)
    : view.layout === "split"
      ? `<div class="split">
           <div class="split-media">${imagesHtml(s, "media")}</div>
           <div class="split-content">${panelsHtml}${notesForm(a)}${nav}</div>
         </div>`
      : `<section>${imagesHtml(s, "thumbs")}</section>${detBadge}${
          view.panels.length > 1 ? `<div class="panes">${panelsHtml}</div>` : panelsHtml
        }${notesForm(a)}${nav}`;

  const previousMedia = document.getElementById("media");
  document.getElementById("view").innerHTML = `
    <section>${heading}</section>
    ${readOnlyBanner}
    ${body}
  `;
  keepMedia(s, previousMedia);

  document.querySelectorAll("[data-scope]").forEach((btn) => {
    if (state.readOnly) {
      btn.disabled = true;
      btn.style.cursor = "not-allowed";
      return;
    }
    btn.addEventListener("click", async () => {
      await mark(btn.dataset.scope, btn.dataset.value);
      save();
    });
  });
  document.getElementById("prev")?.addEventListener("click", () => navigate(-1));
  document.getElementById("next")?.addEventListener("click", () => navigate(1));
  document.querySelectorAll("[data-nav]").forEach((btn) =>
    btn.addEventListener("click", () => navigate(+btn.dataset.nav)),
  );
  const form = document.getElementById("tweaks-form");
  if (form) {
    if (state.readOnly) {
      form.querySelectorAll("textarea, input").forEach((el) => (el.disabled = true));
    } else {
      let t;
      form.addEventListener("input", () => {
        clearTimeout(t);
        t = setTimeout(save, 400);
      });
    }
  }
}

// One panel from the contract, backed by s[panel.source] (model_output or
// ground_truth). The flag control (if any) and the verdict buttons (on the
// model panel) come from the contract too.
function renderPanel(panel, s, a) {
  const obj = s[panel.source] ?? {};
  const flagBtn = panel.flag
    ? `<div class="controls">
        <button data-scope="catalogue" data-value="${escapeHtml(panel.flag.value)}" class="${
          a.catalogue_correct === panel.flag.value ? "selected no" : ""
        }">${escapeHtml(panel.flag.label)} <span class="kbd">f</span></button>
      </div>`
    : "";
  const scoring = panel.source === "model_output" ? scoringButtons(a) : "";
  return `
    <div class="pane">
      <h3>${escapeHtml(panel.title)}</h3>
      ${panelBody(obj, panel.fields)}
      ${flagBtn}
      ${scoring}
    </div>`;
}

function scoringButtons(a) {
  return `
    <div class="controls">
      ${state.view.scoring.verdicts
        .map((v) => {
          // Three verdicts, three colours, matching the ok/warn/bad used for the
          // same values everywhere else.
          // `mid`, not `warn`: .warn is the text-colour utility used in the
          // stats table, and on a button it would recolour the label too.
          const tone = v.negative ? " no" : v.warning ? " mid" : "";
          const sel = a.model_correct === v.value ? `selected${tone}` : "";
          return `<button data-scope="model" data-value="${escapeHtml(v.value)}" class="${sel}">${escapeHtml(
            v.label,
          )} <span class="kbd">${escapeHtml(v.hotkey)}</span></button>`;
        })
        .join("")}
    </div>`;
}

// Free-text notes, shown when the chosen verdict has notes:true in the contract.
function notesForm(a) {
  const { verdicts, notes } = state.view.scoring;
  const cur = verdicts.find((v) => v.value === a.model_correct);
  const show = cur?.notes === true;
  return `
    <form id="tweaks-form" ${show ? "" : "hidden"}>
      <label>${escapeHtml(notes.label)}
        <textarea name="notes" rows="3" placeholder="${escapeHtml(notes.placeholder)}">${escapeHtml(
          a.notes ?? "",
        )}</textarea>
      </label>
    </form>`;
}

function escapeHtml(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[c],
  );
}

// Capture the notes textarea into state before a re-render throws the DOM away,
// so switching verdicts (or a verdict hotkey) mid-sentence doesn't lose the text.
function flushNotes() {
  const form = document.getElementById("tweaks-form");
  if (!form || form.hidden || !state.current) return;
  const a =
    state.current.annotation ??
    (state.current.annotation = { sample_id: String(state.current.id) });
  for (const [k, v] of new FormData(form).entries()) a[k] = String(v);
}

async function mark(scope, value) {
  flushNotes();
  const a = state.current.annotation ?? { sample_id: String(state.current.id) };
  if (scope === "catalogue")
    a.catalogue_correct = a.catalogue_correct === value ? null : value;
  if (scope === "model")
    a.model_correct = a.model_correct === value ? null : value;
  state.current.annotation = a;
  render();
}

async function save() {
  if (state.readOnly) return;
  flushNotes();
  const a = state.current.annotation ?? { sample_id: String(state.current.id) };
  const res = await fetch(api(`api/annotations/${state.current.id}`), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(a),
  });
  const saved = await res.json();
  state.current.annotation = saved;
  // Only count this sample as reviewed if a model score was chosen — rows
  // can also be created by autosaving the notes textarea on navigate.
  state.samples[state.index].annotated = (saved?.model_correct ?? null) !== null;
}

async function navigate(delta) {
  if (isEval()) await flushGold();
  else await save();
  const next = state.index + delta;
  if (next < 0 || next >= state.samples.length) return;
  state.index = next;
  await loadSample();
}

async function jumpToNextUnchecked() {
  await save();
  const start = state.index;
  // Search forward, then wrap to the start.
  for (let i = 1; i <= state.samples.length; i++) {
    const idx = (start + i) % state.samples.length;
    if (!state.samples[idx].annotated) {
      state.index = idx;
      await loadSample();
      return;
    }
  }
}

document.addEventListener("keydown", (e) => {
  if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
  if (currentRoute() !== "review" && currentRoute() !== "eval") return;
  // Navigation works in read-only and in the correction editor.
  if (e.key === "ArrowRight") return navigate(1);
  if (e.key === "ArrowLeft") return navigate(-1);
  // Verdict/flag hotkeys are review-only (the editor has no verdict buttons).
  if (isEval() || state.readOnly || !state.view) return;
  if (e.key === "s" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    return save();
  }
  // 'f' flags the catalogue panel, if the contract defines a flag control.
  const flagPanel = state.view.panels.find((p) => p.flag);
  if (e.key === "f" && flagPanel) return mark("catalogue", flagPanel.flag.value);
  // Verdict hotkeys come from the contract.
  const verdict = state.view.scoring.verdicts.find((v) => v.hotkey === e.key);
  if (verdict) mark("model", verdict.value);
});

// ── Build eval set (correction editor) ─────────────────────────────────
// Surfaces only the rows the model got wrong (needs_tweaks / not_accurate) and
// lets a reviewer edit the fields into a correct answer. A saved edit becomes a
// gold label (POST /api/gold) which `paratext export` ships alongside the
// already-verified good_enough rows. The model verdict is never changed here.
const EVAL_VERDICTS = ["needs_tweaks", "not_accurate"];

async function loadEvalList(targetId = null) {
  const res = await fetch(api("api/samples"));
  state.allSamples = await res.json();
  state.samples = state.allSamples.filter((s) => EVAL_VERDICTS.includes(s.model_correct));
  state.samplesMode = "eval";
  if (!state.samples.length) return renderEvalEmpty();
  let idx = 0;
  if (targetId !== null) {
    const i = state.samples.findIndex((s) => String(s.id) === String(targetId));
    if (i !== -1) idx = i;
  } else {
    const firstUncorrected = state.samples.findIndex((s) => !s.corrected);
    idx = firstUncorrected === -1 ? 0 : firstUncorrected;
  }
  state.index = idx;
  await loadSample();
}

function renderEvalEmpty() {
  document.getElementById("progress").textContent = "";
  const good = state.allSamples.filter((s) => s.model_correct === "good_enough").length;
  const reviewed = state.allSamples.filter((s) => s.model_correct).length;
  document.getElementById("view").innerHTML = `
    <h2>Build eval set</h2>
    <p class="text-light">Nothing to correct — no rows are marked <em>needs tweaks</em> or
      <em>not accurate</em>. ${
        reviewed
          ? `${good} good-enough row${good === 1 ? "" : "s"} ${
              good === 1 ? "is" : "are"
            } already gold.`
          : "Score some rows in Review first."
      }</p>
    <p><a href="#/review" class="button outline small">← Back to review</a></p>`;
}

function evalHeader() {
  const total = state.allSamples.length;
  const good = state.allSamples.filter((s) => s.model_correct === "good_enough").length;
  const queue = state.samples.length;
  const corrected = state.samples.filter((s) => s.corrected).length;
  return `
    <div class="eval-head hstack gap-2">
      <span class="badge" data-variant="secondary">${corrected} / ${queue} corrected</span>
      <span class="badge" data-variant="secondary">${good} good-enough (already gold)</span>
      <span class="badge" data-variant="secondary">eval set so far: ${good + corrected} of ${total}</span>
    </div>`;
}

// Editable control for one field spec, prefilled with `value`. Shared by the
// top-level fields and (recursively) the item fields of an entries editor.
function fieldControl(f, value, inline = false) {
  const key = escapeHtml(f.key);
  if (f.type === "bool") {
    return `<select data-field="${key}" data-type="bool">
      <option value="true" ${value === true ? "selected" : ""}>yes</option>
      <option value="false" ${value === true ? "" : "selected"}>no</option>
    </select>`;
  }
  if (f.type === "enum") {
    const blank = `<option value="" ${
      value == null || value === "" ? "selected" : ""
    }>—</option>`;
    const opts = (f.options ?? [])
      .map((o) => `<option ${String(value) === o ? "selected" : ""}>${escapeHtml(o)}</option>`)
      .join("");
    return `<select data-field="${key}" data-type="enum">${blank}${opts}</select>`;
  }
  if (f.type === "number") {
    return `<input type="number" data-field="${key}" data-type="number" value="${value ?? ""}" />`;
  }
  if (f.type === "list") {
    // Inline (an entry-table cell) → single line, comma-separated; otherwise a
    // textarea, one item per line. readControl splits on either.
    if (inline) {
      return `<textarea data-field="${key}" data-type="list" rows="1" class="autogrow"
        placeholder="comma-separated">${escapeHtml(Array.isArray(value) ? value.join(", ") : "")}</textarea>`;
    }
    const text = Array.isArray(value) ? value.join("\n") : "";
    return `<textarea data-field="${key}" data-type="list" rows="2"
      placeholder="one per line">${escapeHtml(text)}</textarea>`;
  }
  if (f.type === "entries") {
    const list = Array.isArray(value) ? value : [];
    // On a read-only round the inputs can't be saved and clip long values, so
    // show the plain read-only table (text wraps freely) instead.
    if (state.readOnly) {
      return list.length
        ? entriesTable(entryItems(f, list), list)
        : `<p><em>No ${escapeHtml(f.label.toLowerCase())}.</em></p>`;
    }
    return entriesEditor(f, list);
  }
  if (inline) {
    return `<textarea data-field="${key}" data-type="string" rows="1" class="autogrow">${escapeHtml(
      value ?? "",
    )}</textarea>`;
  }
  return `<textarea data-field="${key}" data-type="string" rows="2">${escapeHtml(
    value ?? "",
  )}</textarea>`;
}

// Entries edit as a table — one column per item field, one row per entry, an
// input in each cell. Mirrors the read-only entries table. The add/delete/save
// handlers key off .entry-row and [data-field], so this stays compatible.
function entriesEditor(f, entries) {
  const items = f.item_fields ?? [];
  const head = items.map((it) => `<th>${escapeHtml(it.label)}</th>`).join("") + "<th></th>";
  const rows = entries.map((e) => entryRow(f, e)).join("");
  return `<div class="entries-editor">
    <div class="table"><table class="entry-table">
      <thead><tr>${head}</tr></thead>
      <tbody class="entry-rows">${rows}</tbody>
    </table></div>
    <button type="button" class="outline small mt-2" data-add-entry>+ Add ${escapeHtml(
      f.label.toLowerCase(),
    )}</button>
  </div>`;
}

function entryRow(f, entry) {
  const cells = (f.item_fields ?? [])
    .map((it) => `<td>${fieldControl(it, entry?.[it.key], true)}</td>`)
    .join("");
  return `<tr class="entry-row">${cells}
    <td class="entry-del"><button type="button" class="ghost small" data-del-entry
      aria-label="Remove entry">✕</button></td></tr>`;
}

function modelPanelOf(view) {
  return view.panels.find((p) => p.source === "model_output") ?? view.panels[0];
}

function fieldSpec(key) {
  return modelPanelOf(state.view).fields.find((f) => f.key === key);
}

function renderEditor() {
  const s = state.current;
  const base = s.model_output ?? {};
  const prefill = s.gold?.output ?? base;
  const note = s.annotation?.notes;
  const total = state.samples.length;
  const previousMedia = document.getElementById("media");
  document.getElementById("progress").innerHTML =
    `<span class="sample-label" title="${escapeHtml(String(s.document_id ?? s.id))}"
      >Correcting ${state.index + 1} / ${total} — ${escapeHtml(
        String(s.document_id ?? s.id),
      )}</span>`;

  const fields = modelPanelOf(state.view)
    .fields.filter((f) => !f.collapsed) // auxiliary fields (e.g. the "Debug" notes) aren't gold
    .map((f) => {
      const hint =
        f.type === "entries" ? "" : `<small class="hint">model: ${escapeHtml(fmt(base[f.key]))}</small>`;
      return `<div class="edit-field" data-key="${escapeHtml(f.key)}" data-type="${escapeHtml(
        f.type,
      )}">
        <label class="k">${escapeHtml(f.label)}</label>
        <div>${fieldControl(f, prefill[f.key])}${hint}</div>
      </div>`;
    })
    .join("");

  const atFirst = state.index === 0;
  const atLast = state.index === total - 1;
  const readOnlyBanner = state.readOnly
    ? `<aside class="readonly-banner">This round is archived (read-only). Corrections can't be saved.
        <a href="#/select">Switch round →</a></aside>`
    : "";

  document.getElementById("view").innerHTML = `
    <section><h2>Build eval set ${s.gold ? goldBadgeHtml() : ""}</h2></section>
    ${evalHeader()}
    ${readOnlyBanner}
    <div class="split">
      <div class="split-media">
        ${note
          ? `<div role="alert" data-variant="warning" class="eval-note">
               <div><strong>Reviewer note</strong><br>${escapeHtml(note)}</div>
             </div>`
          : ""}
        ${imagesHtml(s, "media")}
      </div>
      <div class="split-content">
        <form id="editor">${fields}</form>
        <div class="controls">
          <button id="ev-prev" ${atFirst ? "disabled" : ""}>← Previous</button>
          <button id="ev-clear" class="outline" ${s.gold ? "" : "disabled"}>Clear correction</button>
          ${
            atLast
              ? `<a href="#/stats" class="button primary">Done — see results →</a>`
              : `<button id="ev-next" class="primary">Save &amp; next →</button>`
          }
        </div>
      </div>
    </div>`;

  keepMedia(s, previousMedia);

  const editor = document.getElementById("editor");
  if (state.readOnly) {
    editor.querySelectorAll("input, textarea, select, button").forEach((el) => (el.disabled = true));
  } else {
    wireEditor(editor);
  }
  autogrow(editor.querySelectorAll("textarea.autogrow"));
  document.getElementById("ev-prev").addEventListener("click", () => navigate(-1));
  document.getElementById("ev-next")?.addEventListener("click", () => navigate(1));
  document.getElementById("ev-clear").addEventListener("click", clearGold);
}

function goldBadgeHtml() {
  return `<span class="gold-badge">✓ saved as gold</span>`;
}

function wireEditor(editor) {
  editor.addEventListener("click", (e) => {
    const add = e.target.closest("[data-add-entry]");
    const del = e.target.closest("[data-del-entry]");
    if (add) {
      const wrap = add.closest(".edit-field");
      const rows = wrap.querySelector(".entry-rows");
      rows.insertAdjacentHTML("beforeend", entryRow(fieldSpec(wrap.dataset.key), {}));
      autogrow(rows.lastElementChild.querySelectorAll("textarea.autogrow"));
      markDirty();
    } else if (del) {
      del.closest(".entry-row").remove();
      markDirty();
    }
  });
  editor.addEventListener("input", (e) => {
    if (e.target.matches("textarea.autogrow")) autogrow([e.target]);
    markDirty();
    clearTimeout(state.evalTimer);
    state.evalTimer = setTimeout(saveGold, 500);
  });
}

// Size cell textareas to their content so long values wrap and grow the row
// rather than clipping. Runs on render and on each edit of an .autogrow cell.
function autogrow(els) {
  els.forEach((el) => {
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  });
}

function markDirty() {
  state.evalDirty = true;
}

function readControl(el) {
  const t = el.dataset.type;
  if (t === "bool") return el.value === "true";
  if (t === "enum") return el.value === "" ? null : el.value;
  if (t === "number") return el.value === "" ? null : Number(el.value);
  // Split on newline (textarea, one per line) or comma (inline entry-cell input).
  if (t === "list") return el.value.split(/[\n,]/).map((x) => x.trim()).filter(Boolean);
  return el.value.trim() === "" ? null : el.value; // string
}

// Read the editor form back into a full output object (all schema fields).
function collectEdits() {
  const editor = document.getElementById("editor");
  const out = {};
  editor.querySelectorAll(":scope > .edit-field").forEach((wrap) => {
    const key = wrap.dataset.key;
    if (wrap.dataset.type === "entries") {
      out[key] = [...wrap.querySelectorAll(".entry-row")].map((row) => {
        const obj = {};
        row.querySelectorAll("[data-field]").forEach((ctl) => {
          obj[ctl.dataset.field] = readControl(ctl);
        });
        return obj;
      });
    } else {
      const ctl = wrap.querySelector("[data-field]");
      out[key] = ctl ? readControl(ctl) : null;
    }
  });
  return out;
}

// Stable stringify (sorted keys) so change detection ignores key order.
function canon(v) {
  if (Array.isArray(v)) return "[" + v.map(canon).join(",") + "]";
  if (v && typeof v === "object")
    return (
      "{" +
      Object.keys(v)
        .sort()
        .map((k) => JSON.stringify(k) + ":" + canon(v[k]))
        .join(",") +
      "}"
    );
  return JSON.stringify(v ?? null);
}

async function saveGold() {
  if (state.readOnly || !state.current || !document.getElementById("editor")) return;
  const output = collectEdits();
  const base = state.current.model_output ?? {};
  const fields = Object.keys(output).filter((k) => canon(output[k]) !== canon(base[k]));
  const res = await fetch(api(`api/gold/${state.current.id}`), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ output, fields }),
  });
  state.current.gold = await res.json();
  state.evalDirty = false;
  for (const list of [state.samples, state.allSamples]) {
    const q = list.find((x) => String(x.id) === String(state.current.id));
    if (q) q.corrected = true;
  }
  reflectGoldState();
}

// Update the gold badge / header / Clear button in place (no re-render, so the
// autosave never steals focus mid-typing).
function reflectGoldState() {
  const hasGold = !!state.current.gold;
  const h2 = document.querySelector("#view h2");
  let badge = document.querySelector(".gold-badge");
  if (hasGold && !badge && h2) h2.insertAdjacentHTML("beforeend", " " + goldBadgeHtml());
  if (!hasGold && badge) badge.remove();
  const clear = document.getElementById("ev-clear");
  if (clear) clear.disabled = !hasGold;
  const head = document.querySelector(".eval-head");
  if (head) head.outerHTML = evalHeader();
}

async function flushGold() {
  clearTimeout(state.evalTimer);
  if (state.evalDirty) await saveGold();
}

async function clearGold() {
  if (state.readOnly || !state.current) return;
  clearTimeout(state.evalTimer);
  await fetch(api(`api/gold/${state.current.id}`), { method: "DELETE" });
  state.current.gold = null;
  state.evalDirty = false;
  for (const list of [state.samples, state.allSamples]) {
    const q = list.find((x) => String(x.id) === String(state.current.id));
    if (q) q.corrected = false;
  }
  renderEditor();
}

// ── Stats view ────────────────────────────────────────────────────────
// LCS-based line diff. ~100 lines × 100 lines is trivial; no need for
// a Myers-style algorithm.
function lineDiff(oldText, newText) {
  const a = oldText.split("\n");
  const b = newText.split("\n");
  const m = a.length;
  const n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1] + 1
          : Math.max(dp[i - 1][j], dp[i][j - 1]);
    }
  }
  const out = [];
  let i = m;
  let j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      out.push({ t: "=", text: a[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      out.push({ t: "+", text: b[j - 1] });
      j--;
    } else {
      out.push({ t: "-", text: a[i - 1] });
      i--;
    }
  }
  return out.reverse();
}

function renderDiff(oldText, newText) {
  const lines = lineDiff(oldText, newText);
  const styles = {
    "+": "color:var(--success); background:color-mix(in srgb, var(--success) 10%, transparent);",
    "-": "color:var(--danger); background:color-mix(in srgb, var(--danger) 10%, transparent);",
    "=": "color:var(--muted-foreground);",
  };
  return lines
    .map(
      (l) =>
        `<div style="${styles[l.t]} padding:0 .5rem; white-space:pre-wrap;">${
          l.t === "=" ? " " : l.t
        } ${escapeHtml(l.text)}</div>`,
    )
    .join("");
}

function renderPromptsPanel(prompts) {
  if (!prompts.length) {
    return `<details style="margin:1rem 0;"><summary><strong>Prompt history</strong> <small style="color:var(--muted-foreground);">(no prompt text recorded)</small></summary></details>`;
  }
  const items = prompts
    .map(
      (p, i) => {
        const rounds = (p.rounds ?? []).length
          ? `round${p.rounds.length === 1 ? "" : "s"} ${p.rounds.join(", ")}`
          : "";
        const isLatest = i === 0;
        // Only the latest panel gets a diff toggle (diff vs the immediately
        // preceding prompt). Older panels are display-only.
        const previous = isLatest ? prompts[1] : null;
        const diffToggle = previous
          ? `<div style="margin-top:.5rem;">
              <button type="button" class="outline small" data-diff-against="${escapeHtml(previous.hash)}" data-diff-self="${escapeHtml(p.hash)}">
                Difference vs previous round
              </button>
            </div>`
          : "";
        return `
      <details ${isLatest ? "open" : ""} style="margin:.5rem 0;">
        <summary>
          <code>${escapeHtml(p.hash)}</code>
          <small style="color:var(--muted-foreground); margin-left:.5rem;">
            ${rounds ? escapeHtml(rounds) + " · " : ""}${p.count} record${p.count === 1 ? "" : "s"}${isLatest ? " · latest" : ""}
          </small>
        </summary>
        ${diffToggle}
        <div data-prompt-body="${escapeHtml(p.hash)}" style="margin-top:.5rem;">
          <pre class="prompt-text">${escapeHtml(
            p.text,
          )}</pre>
        </div>
      </details>`;
      },
    )
    .join("");
  return `
    <details style="margin:1rem 0;">
      <summary><strong>Prompt history</strong> <small style="color:var(--muted-foreground);">(${prompts.length} version${prompts.length === 1 ? "" : "s"})</small></summary>
      <div style="margin-top:.5rem;">${items}</div>
    </details>
  `;
}


// ── Fields panel ──────────────────────────────────────────────────────
// The schema in the terms someone meeting one for the first time can read:
// what the model is asked to fill in, and what changed since last round.
// A table, not a +/- diff — the audience for this is learning what a field is.

const TYPE_WORDS = {
  string: "text",
  integer: "whole number",
  number: "number",
  boolean: "yes / no",
  array: "list",
  object: "group",
};

const typeWord = (t) => TYPE_WORDS[t] ?? (t ?? "text");

function renderFieldsPanel(rounds) {
  if (!rounds || !rounds.length) return "";
  const latest = rounds[rounds.length - 1];
  if (!latest.fields.length) return "";

  // Where each field entered, so an unchanged row can still say "since r1".
  const firstSeen = new Map();
  for (const r of rounds) {
    for (const f of r.fields) if (!firstSeen.has(f.key)) firstSeen.set(f.key, r.round);
  }
  const c = latest.changes ?? { added: [], removed: [], retyped: [] };
  const addedKeys = new Set(c.added.map((f) => f.key));
  const retyped = new Map(c.retyped.map((f) => [f.key, f]));

  const multi = rounds.length > 1;
  const status = (f) => {
    if (!multi) return "";
    if (addedKeys.has(f.key))
      return `<span class="ok">new this round</span>`;
    const rt = retyped.get(f.key);
    if (rt)
      return `<span class="warn">was ${escapeHtml(typeWord(rt.from))}</span>`;
    const seen = firstSeen.get(f.key);
    return `<span class="text-light">since round ${seen ?? 1}</span>`;
  };

  const rows = latest.fields
    .map(
      (f) => `<tr>
        <td><code>${escapeHtml(f.key)}</code></td>
        <td>${escapeHtml(f.label ?? f.key)}</td>
        <td>${escapeHtml(typeWord(f.type))}</td>
        <td>${status(f)}</td>
      </tr>`,
    )
    .join("");

  const gone = (c.removed ?? [])
    .map(
      (f) =>
        `<tr class="text-light"><td><code>${escapeHtml(f.key)}</code></td>
         <td>${escapeHtml(f.label ?? f.key)}</td>
         <td>${escapeHtml(typeWord(f.type))}</td>
         <td class="bad">dropped this round</td></tr>`,
    )
    .join("");

  const changed =
    (c.added?.length ?? 0) + (c.removed?.length ?? 0) + (c.retyped?.length ?? 0);
  const summary =
    rounds.length < 2
      ? `${latest.fields.length} field${latest.fields.length === 1 ? "" : "s"}`
      : changed === 0
        ? `${latest.fields.length} fields · unchanged since round ${
            rounds[rounds.length - 2].round
          }`
        : `${latest.fields.length} fields · ${changed} change${
            changed === 1 ? "" : "s"
          } this round`;

  return `<details style="margin:1rem 0;">
    <summary><strong>Fields</strong> <small style="color:var(--muted-foreground);">(${escapeHtml(
      summary,
    )})</small></summary>
    <p class="text-light mt-2" style="font-size:.875rem;">
      One row per piece of metadata the model is asked to produce for every card.
      Together they are the <em>schema</em>. Change them in
      <code>schema.py</code>; describe them in <code>prompt.md</code>.
    </p>
    <div class="table"><table>
      <thead><tr><th>Field</th><th>Shown as</th><th>Holds</th><th></th></tr></thead>
      <tbody>${rows}${gone}</tbody>
    </table></div>
  </details>`;
}


// ── Prompt drift ──────────────────────────────────────────────────────
// The one diagnostic the Projects page carried that nothing else does: does
// the *installed* prompt still match what this round was run with? Silent when
// no matching project is installed — reviewing a packaged round on a machine
// that never ran it is normal.
function renderDriftPanel(projects, schema) {
  const p = (projects ?? []).find((x) => x.name === schema);
  if (!p) return "";
  const lr = p.latest_round;
  const audit = (p.audit ?? []).length ? auditPill(p.audit) : "";
  if (!lr) return audit ? `<p class="mt-2">${audit}</p>` : "";
  const label = `round ${escapeHtml(String(lr.round))}`;
  if (lr.matches_installed) {
    return `<p class="text-light" style="font-size:.875rem;">
      Prompt matches the installed project ${audit}</p>`;
  }
  return `<div class="mt-2">
    <p class="bad"><strong>Prompt differs</strong> from ${label}
      (<code>${escapeHtml(lr.dataset)}</code>) — a new run will not reproduce it. ${audit}</p>
    <details class="mt-2"><summary>Diff — ${label} → installed</summary>
      <pre class="mt-2" style="font-size:.8125rem;">${renderDiff(lr.prompt, p.prompt)}</pre>
    </details>
  </div>`;
}


// ── Round switcher ────────────────────────────────────────────────────
// Rounds are history of one dataset, not a choice of dataset, so they live
// here rather than on the index. The current round is marked; archived ones
// say so, because they are read-only.
function renderRoundSwitcher(current) {
  const group = groupDatasets(state.datasets).find((g) => g.base === current.base);
  if (!group || group.rounds.length < 2) return "";
  const chips = group.rounds
    .map((d) => {
      const here = d.name === current.name;
      const cls = here ? "button small" : "button outline small";
      const tag = d.active === false ? " · archived" : "";
      return `<button class="${cls}" data-round="${escapeHtml(d.name)}"
        ${here ? "aria-current=\"page\"" : ""}>round ${d.round}${tag}</button>`;
    })
    .join("");
  return `<div class="controls" role="group" aria-label="Round">${chips}</div>`;
}

async function renderStats() {
  const [statsRes, tableRes, promptsRes, schemaRes, projectsRes] = await Promise.all([
    fetch(api("api/stats")),
    fetch(api("api/table")),
    fetch(api("api/prompts")),
    fetch(api("api/schema")),
    fetch("api/projects"),
  ]);
  const s = await statsRes.json();
  const rows = await tableRes.json();
  const promptsData = await promptsRes.json();
  const schemaData = await schemaRes.json();
  const projects = await projectsRes.json().catch(() => []);
  document.getElementById("progress").textContent = "";

  const badge = (v) => {
    if (v === "good_enough") return `<span class="ok">Good enough</span>`;
    if (v === "needs_tweaks") return `<span class="warn">Needs tweaks</span>`;
    if (v === "not_accurate") return `<span class="bad">Not accurate</span>`;
    return `<span class="text-light">—</span>`;
  };

  // Stats display is driven by the contract: which exports apply, whether a
  // flag count is meaningful, and the table column headers.
  const view = state.view;
  const hasFlag = view.panels.some((p) => p.flag);
  const tl = view.table_label;
  const titleHeader =
    (tl &&
      view.panels
        .find((p) => p.source === tl.source)
        ?.fields.find((f) => f.key === tl.key)?.label) ||
    "Title";
  const exportLinks = (view.exports ?? [])
    .map(
      (exp) =>
        `<a href="${api("api/export/" + exp.id)}" class="button outline small" download>${escapeHtml(
          exp.label,
        )}</a>`,
    )
    .join("");

  document.getElementById("view").innerHTML = `
    <div class="results-head">
      <h2>Results — ${escapeHtml(s.dataset)}
        <small class="text-light">(${escapeHtml(s.schema)})</small></h2>
      <div class="eval-cta">
        <div class="eval-cta-row">
          <span class="gold-ring"><a href="#/eval" class="button primary gold-cta">
            Build eval set
            <span class="gold-count">${s.eval_gold ?? s.model.good_enough}</span>
          </a></span>
          <button class="button outline" id="open-export">Export…</button>
        </div>
        <p class="text-light eval-cta-note">${s.model.good_enough} good-enough +
          ${s.corrected ?? 0} human-corrected</p>
      </div>
    </div>

    ${renderRoundSwitcher(state.datasets.find((d) => d.name === s.dataset) ?? {})}

    <dl>
      <div class="field-row"><dt>Reviewed</dt><dd>${s.annotated} of ${s.total} (${
        s.total ? ((s.annotated / s.total) * 100).toFixed(0) : 0
      }%)</dd></div>
      <div class="field-row"><dt>Accuracy score</dt><dd><strong>${
        s.model.accuracy !== null ? s.model.accuracy.toFixed(1) + "%" : "—"
      }</strong> <small>(good=1.0, tweaks=0.5, inaccurate=0 · ${s.model.scored} scored)</small></dd></div>
      <div class="field-row"><dt>Good enough</dt><dd class="ok">${s.model.good_enough}</dd></div>
      <div class="field-row"><dt>Needs tweaks</dt><dd class="warn">${s.model.needs_tweaks}</dd></div>
      <div class="field-row"><dt>Not accurate</dt><dd class="bad">${s.model.not_accurate}</dd></div>
      ${hasFlag ? `<div class="field-row"><dt>Flagged</dt><dd>${s.flagged_marc}</dd></div>` : ""}
    </dl>

    ${renderDriftPanel(projects, s.schema)}

    ${renderPromptsPanel(promptsData.prompts ?? [])}

    ${renderFieldsPanel(schemaData.rounds ?? [])}

    ${
      state.workshop
        ? `<div class="controls"><a href="#/workshop" class="button outline small">Prompt editor</a></div>`
        : ""
    }

    ${exportLinks ? `<div class="controls">${exportLinks}</div>` : ""}

    <div class="table">
    <table>
      <thead>
        <tr>
          <th>${escapeHtml(view.id_label ?? "ID")}</th>
          <th>${escapeHtml(titleHeader)}</th>
          <th class="score-col">Model score</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (r) => `
          <tr class="row-link" onclick="location.hash='#/review/${escapeHtml(r.sample_id)}'">
            <td><code>${escapeHtml(r.document_id ?? r.sample_id)}</code></td>
            <td>${escapeHtml(r.title ?? "—")}</td>
            <td>${badge(r.model_correct)}</td>
            <td class="note-cell">${r.notes ? escapeHtml(r.notes) : ""}</td>
          </tr>`,
          )
          .join("")}
      </tbody>
    </table>
    </div>
  `;

  document.getElementById("open-export")?.addEventListener("click", openExportModal);

  document.querySelectorAll("[data-round]").forEach((btn) => {
    btn.addEventListener("click", () => {
      setDataset(btn.dataset.round);
      route();
    });
  });

  // Wire up "Diff vs latest" toggles in the prompt history panel.
  const promptByHash = new Map(
    (promptsData.prompts ?? []).map((p) => [p.hash, p]),
  );
  document.querySelectorAll("[data-diff-against]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const selfHash = btn.dataset.diffSelf;
      const otherHash = btn.dataset.diffAgainst;
      const self = promptByHash.get(selfHash);
      const other = promptByHash.get(otherHash);
      const body = document.querySelector(`[data-prompt-body="${CSS.escape(selfHash)}"]`);
      if (!self || !other || !body) return;
      const showingDiff = btn.dataset.mode === "diff";
      if (showingDiff) {
        body.innerHTML = `<pre class="prompt-text">${escapeHtml(
          self.text,
        )}</pre>`;
        btn.textContent = "Difference vs previous round";
        btn.dataset.mode = "full";
      } else {
        // Diff base = previous prompt; new = current. So +/- read as
        // "what was added/removed since the previous round".
        body.innerHTML = `<pre style="font-size:.8125rem;">${renderDiff(
          other.text,
          self.text,
        )}</pre>`;
        btn.textContent = "Show full text";
        btn.dataset.mode = "diff";
      }
    });
  });
}

// ── Export modal ──────────────────────────────────────────────────────
// A native <dialog> (Oat-styled) over the /api/export/* endpoints. Format-first
// tabs; a records-scope row (verdict-coloured dots) that governs MARC/DC/JSONL;
// an editable mapping table whose edits are POSTed with the download. HF is a
// placeholder until sign-in lands (CLI for now).
const DC_ELEMENTS = ["title", "creator", "subject", "description", "publisher",
  "contributor", "date", "type", "format", "identifier", "source", "language",
  "relation", "coverage", "rights"];

function scopeDots(scope) {
  if (scope === "good_enough") return `<span class="dots d1"><span style="background:var(--success)"></span></span>`;
  if (scope === "needs_tweaks") return `<span class="dots d2"><span style="background:var(--success)"></span><span style="background:var(--warning)"></span></span>`;
  return `<span class="dots d3"><span style="background:var(--success)"></span><span style="background:var(--warning)"></span><span style="background:var(--danger)"></span></span>`;
}

// Hugging Face sign-in (OAuth 2.0 Authorization Code + PKCE, public client).
// The token is the user's and lives only in this tab (sessionStorage); the
// server proxies the code→token exchange but stores nothing. See hf_oauth.py.
const HF_LICENSES = ["cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0", "apache-2.0", "mit", "other"];

function loadHfAuth() {
  try { return JSON.parse(sessionStorage.getItem("paratext_hf")) || null; } catch { return null; }
}
let hfAuth = loadHfAuth();
function saveHfAuth(a) {
  hfAuth = a;
  if (a) sessionStorage.setItem("paratext_hf", JSON.stringify(a));
  else sessionStorage.removeItem("paratext_hf");
}

function b64url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
async function pkcePair() {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return { verifier, challenge: b64url(digest) };
}

// Resolve once the popup hands the code back; `state` guards against CSRF. HF's
// COOP severs window.opener, so we listen on BroadcastChannel and the storage
// event (both same-origin, COOP-proof) as well as postMessage.
function awaitOAuth(stateTok) {
  return new Promise((resolve, reject) => {
    const bc = "BroadcastChannel" in window ? new BroadcastChannel("paratext-hf-oauth") : null;
    const timer = setTimeout(() => { done(); reject(new Error("sign-in timed out")); }, 180000);
    function handle(d) {
      if (!d || d.source !== "paratext-hf-oauth" || d.state !== stateTok) return;
      done();
      resolve(d);
    }
    function onMsg(e) { if (e.origin === window.location.origin) handle(e.data); }
    function onStorage(e) {
      if (e.key !== "paratext-hf-oauth" || !e.newValue) return;
      try { handle(JSON.parse(e.newValue)); localStorage.removeItem("paratext-hf-oauth"); } catch { /* ignore */ }
    }
    function done() {
      clearTimeout(timer);
      window.removeEventListener("message", onMsg);
      window.removeEventListener("storage", onStorage);
      if (bc) { bc.onmessage = null; bc.close(); }
    }
    if (bc) bc.onmessage = (e) => handle(e.data);
    window.addEventListener("message", onMsg);
    window.addEventListener("storage", onStorage);
  });
}

async function hfSignIn() {
  const cfg = await (await fetch(api("api/export/hf/config"))).json();
  const { verifier, challenge } = await pkcePair();
  const stateTok = b64url(crypto.getRandomValues(new Uint8Array(16)));
  const url = `${cfg.authorize_url}?${new URLSearchParams({
    client_id: cfg.client_id, redirect_uri: cfg.redirect_uri, response_type: "code",
    scope: cfg.scopes, state: stateTok, code_challenge: challenge, code_challenge_method: "S256",
  })}`;
  const popup = window.open(url, "hf-oauth", "width=680,height=820");
  if (!popup) throw new Error("popup blocked — allow popups for this site, then retry");
  const msg = await awaitOAuth(stateTok);
  try { popup.close(); } catch { /* COOP may block; the callback also self-closes */ }
  if (msg.error) throw new Error(msg.error_description || msg.error);
  const res = await fetch(api("api/oauth/hf/exchange"), {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ code: msg.code, code_verifier: verifier,
      redirect_uri: cfg.redirect_uri, client_id: cfg.client_id }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "sign-in failed");
  saveHfAuth({ token: data.access_token, user: data.user || {} });
}

async function openExportModal() {
  const dataset = state.dataset;
  const dsInfo = (state.datasets || []).find((d) => d.name === dataset);
  const schema = dsInfo ? dsInfo.schema : "";

  const dlg = document.createElement("dialog");
  dlg.className = "export-dialog";
  document.body.appendChild(dlg);
  const ex = { fmt: "marc", scope: "everything", meta: { marc: null, dc: null },
    edits: { marc: {}, dc: {} }, hf: {}, hfCfg: null, aiNote: null };

  async function meta(fmt) {
    if (!ex.meta[fmt]) {
      const res = await fetch(api("api/export/fields", { fmt }));
      ex.meta[fmt] = await res.json();
    }
    // Seeded once from config, then owned by the user for the rest of the session.
    if (ex.aiNote === null && ex.meta[fmt].ai_note) {
      ex.aiNote = { ...ex.meta[fmt].ai_note };
    }
    return ex.meta[fmt];
  }

  function scopeRow(scopes) {
    const b = (sc, label) => `<button data-scope="${sc}" aria-pressed="${ex.scope === sc}">
      ${scopeDots(sc)} ${label} <span class="n">${scopes[sc]}</span></button>`;
    return `<div class="ex-scope"><span class="ex-scope-label">Records to export</span>
      <div class="ex-scope-btns">
        ${b("good_enough", "Good enough")}${b("needs_tweaks", "Good enough &amp; needs tweaks")}${b("everything", "Everything")}
      </div></div>`;
  }

  function mappingTable(m) {
    const fmt = ex.fmt;
    const rows = m.fields.map((f) => {
      const skipped = ex.skips[fmt][f.key] === true;
      const edited = f.key in ex.edits[fmt];
      const val = edited ? ex.edits[fmt][f.key] : (f.target ?? "");
      const control = fmt === "marc"
        ? `<input class="marc" type="text" data-field="${escapeHtml(f.key)}" value="${escapeHtml(val)}" placeholder="245$a"${skipped ? " disabled" : ""}>`
        : `<select data-field="${escapeHtml(f.key)}"${skipped ? " disabled" : ""}>
             <option value=""${val ? "" : " selected"}>— none —</option>
             ${DC_ELEMENTS.map((e) => `<option${e === val ? " selected" : ""}>${e}</option>`).join("")}
           </select>`;
      return `<tr class="${skipped ? "skipped" : ""}">
        <td class="fname">${escapeHtml(f.key)}</td>
        <td>${control}</td>
        <td class="skip"><input type="checkbox" role="switch" data-skip="${escapeHtml(f.key)}"${skipped ? " checked" : ""} aria-label="skip ${escapeHtml(f.key)}"></td>
      </tr>`;
    }).join("");
    return `<div class="table"><table class="ex-map">
      <thead><tr><th style="width:42%">Field</th><th>${fmt === "marc" ? "MARC tag$subfield" : "DC element"}</th><th class="skip">Skip</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
  }

  function aiNoteRow() {
    const n = ex.aiNote || { enabled: false, text: "" };
    return `<div class="ex-ainote">
      <label class="ex-ainote-toggle">
        <input type="checkbox" data-ainote-on${n.enabled ? " checked" : ""}>
        Add an AI-assistance note
        <span class="hint">${ex.fmt === "marc" ? "MARC 588, first indicator 0" : "an extra dc:description"}</span>
      </label>
      <input class="ex-ainote-text" type="text" data-ainote-text
        value="${escapeHtml(n.text || "")}"${n.enabled ? "" : " disabled"}
        aria-label="AI-assistance note text">
    </div>`;
  }

  function bodyHtml(m) {
    if (ex.fmt === "hf") return hfBody();
    return mappingTable(m) + aiNoteRow();
  }

  function hfBody() {
    const cfg = ex.hfCfg || {};
    const gaps = cfg.provenance_missing || [];
    const warn = gaps.length
      ? `<p class="ex-hf-status warn">⚠ No recorded provenance for ${gaps.map(escapeHtml).join(", ")} —
         publishing works, but the card will read “unknown” for these until you fill them in on the
         dataset card on Hugging Face.</p>`
      : "";
    if (!hfAuth) {
      return `<div class="ex-hf">
        ${warn}
        <button class="button" data-hf-signin>Sign in with Hugging Face</button>
        <p class="ex-hf-status" data-hf-status></p>
      </div>`;
    }
    const user = hfAuth.user || {};
    const owners = [user.name, ...(user.orgs || [])].filter(Boolean);
    const dflt = cfg.default_repo || "";
    const owner = ex.hf.owner ?? (dflt.includes("/") ? dflt.split("/")[0] : user.name);
    const name = ex.hf.name ?? (dflt.includes("/") ? dflt.split("/").slice(1).join("/") : `${schema}-eval`);
    const lic = ex.hf.license ?? cfg.default_license ?? "";
    return `<div class="ex-hf">
      ${warn}
      <p class="ex-hf-id">Signed in as <strong>${escapeHtml(user.name || "—")}</strong>
        <button class="button ghost small" data-hf-signout>Sign out</button></p>
      <div class="ex-hf-form">
        <label>Publish to<select data-hf="owner">${owners.map((o) =>
          `<option${o === owner ? " selected" : ""}>${escapeHtml(o)}</option>`).join("")}</select></label>
        <label>Dataset name<input data-hf="name" value="${escapeHtml(name)}" placeholder="${escapeHtml(schema)}-eval"></label>
        <label>Licence<select data-hf="license">
          <option value=""${lic ? "" : " selected"}>— none —</option>
          ${HF_LICENSES.map((l) => `<option${l === lic ? " selected" : ""}>${escapeHtml(l)}</option>`).join("")}</select></label>
        <label class="ex-hf-vis"><input type="checkbox" role="switch" data-hf="public"${ex.hf.public ? " checked" : ""}> Public dataset</label>
      </div>
      <p class="ex-hf-status" data-hf-status></p>
    </div>`;
  }

  function setHfStatus(msg, isErr = false, url = null) {
    const el = dlg.querySelector("[data-hf-status]");
    if (!el) return;
    el.className = "ex-hf-status" + (isErr ? " bad" : "");
    el.innerHTML = escapeHtml(msg) +
      (url ? ` <a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(url)}</a>` : "");
  }

  function captureHf() {
    dlg.querySelectorAll("[data-hf]").forEach((el) => {
      ex.hf[el.dataset.hf] = el.type === "checkbox" ? el.checked : el.value.trim();
    });
  }

  async function hfPublish() {
    captureHf();
    const owner = ex.hf.owner || hfAuth.user.name;
    const name = (ex.hf.name || "").trim();
    if (!name) return setHfStatus("Enter a dataset name.", true);
    const repo = `${owner}/${name}`;
    setHfStatus(`Publishing ${repo}…`);
    const btn = dlg.querySelector("[data-hf-publish]");
    if (btn) btn.disabled = true;
    try {
      const res = await fetch(api("api/export/hf"), {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${hfAuth.token}` },
        body: JSON.stringify({ repo, public: !!ex.hf.public, license: ex.hf.license || null }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 401) { saveHfAuth(null); render(); }
        throw new Error(data.error || "publish failed");
      }
      setHfStatus(`Published ${data.gold} record${data.gold === 1 ? "" : "s"} →`, false, data.url);
    } catch (e) {
      setHfStatus(e.message, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function render() {
    if (ex.fmt === "hf" && !ex.hfCfg) {
      try { ex.hfCfg = await (await fetch(api("api/export/hf/config"))).json(); }
      catch { ex.hfCfg = {}; }
    }
    const m = ex.fmt === "hf" ? null : await meta(ex.fmt);
    const scopes = (ex.meta.marc || ex.meta.dc || m || {}).scopes || { good_enough: 0, needs_tweaks: 0, everything: 0 };
    const n = scopes[ex.scope];
    const tab = (f, label) => `<button role="tab" aria-selected="${ex.fmt === f}" data-fmt="${f}">${label}</button>`;
    dlg.innerHTML = `
      <header>
        <h3>Export <span class="text-light" style="font-size:.8125rem;">${escapeHtml(dataset)}</span></h3>
        <button class="button ghost small" data-close aria-label="Close">✕</button>
      </header>
      <div>
        ${ex.fmt === "hf" ? "" : scopeRow(scopes)}
        <div role="tablist" style="margin-bottom:1rem;">${tab("marc", "MARC")}${tab("dc", "Dublin Core")}${tab("hf", "Hugging Face")}</div>
        ${bodyHtml(m)}
      </div>
      <footer>
        <a class="button ghost small" data-jsonl download>JSONL + review ↓</a>
        ${ex.fmt === "hf"
          ? `<span class="ex-note">${(ex.hfCfg || {}).gold_count ?? 0} gold record${((ex.hfCfg || {}).gold_count === 1) ? "" : "s"} → the Hub</span>`
          : `<span class="ex-note">${n} record${n === 1 ? "" : "s"} → <span class="fname">${escapeHtml(dataset)}-${ex.fmt}.xml</span></span>`}
        <span class="grow"></span>
        <button class="button outline" data-close>Close</button>
        ${ex.fmt === "hf"
          ? (hfAuth ? `<button class="button" data-hf-publish>Publish to Hub</button>` : "")
          : `<button class="button" data-download>Download ${ex.fmt === "marc" ? "MARCXML" : "XML"}</button>`}
      </footer>`;
    wire();
  }

  function captureEdits() {
    if (ex.fmt === "hf") return;
    dlg.querySelectorAll("[data-field]").forEach((el) => {
      ex.edits[ex.fmt][el.dataset.field] = ex.skips[ex.fmt][el.dataset.field] ? "" : el.value.trim();
    });
    // Keep typed note text across a re-render (a format or scope switch).
    const note = dlg.querySelector("[data-ainote-text]");
    if (note) ex.aiNote = { ...(ex.aiNote || {}), text: note.value };
  }

  async function download() {
    captureEdits();
    const res = await fetch(api(`api/export/${ex.fmt}`), {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({
        scope: ex.scope,
        mapping: ex.edits[ex.fmt],
        ai_note: ex.aiNote && ex.aiNote.enabled ? ex.aiNote.text : "",
      }),
    });
    if (!res.ok) { alert("Export failed: " + (await res.text())); return; }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${dataset}-${ex.fmt}.xml`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function close() {
    document.body.style.overflow = "";
    dlg.close();
    dlg.remove();
  }

  function wire() {
    dlg.querySelectorAll("[data-close]").forEach((b) => (b.onclick = close));
    dlg.querySelectorAll("[data-fmt]").forEach((b) => (b.onclick = () => { captureEdits(); ex.fmt = b.dataset.fmt; render(); }));
    dlg.querySelectorAll("[data-scope]").forEach((b) => (b.onclick = () => { captureEdits(); ex.scope = b.dataset.scope; render(); }));
    dlg.querySelectorAll("[data-skip]").forEach((cb) => (cb.onchange = () => {
      captureEdits();
      ex.skips[ex.fmt][cb.dataset.skip] = cb.checked;
      render();
    }));
    const noteOn = dlg.querySelector("[data-ainote-on]");
    if (noteOn) noteOn.onchange = () => {
      captureEdits();
      ex.aiNote = { ...(ex.aiNote || {}), enabled: noteOn.checked };
      render();
    };
    const dl = dlg.querySelector("[data-download]");
    if (dl) dl.onclick = download;
    // JSONL is always the full round — the review.jsonl alongside it is what
    // you filter with, so scope doesn't apply here.
    const jl = dlg.querySelector("[data-jsonl]");
    if (jl) jl.setAttribute("href", api("api/export/jsonl", { scope: "everything" }));
    // Hugging Face tab.
    const signin = dlg.querySelector("[data-hf-signin]");
    if (signin) signin.onclick = async () => {
      setHfStatus("Opening Hugging Face…");
      try { await hfSignIn(); render(); }
      catch (e) { setHfStatus(e.message, true); }
    };
    const signout = dlg.querySelector("[data-hf-signout]");
    if (signout) signout.onclick = () => { saveHfAuth(null); render(); };
    dlg.querySelectorAll("[data-hf]").forEach((el) => (el.onchange = captureHf));
    const pub = dlg.querySelector("[data-hf-publish]");
    if (pub) pub.onclick = hfPublish;
  }

  ex.skips = { marc: {}, dc: {} };
  dlg.addEventListener("close", close);  // Esc key
  await render();
  document.body.style.overflow = "hidden";  // scroll-lock the page behind the modal
  dlg.showModal();
}


// ── Workshop editor ───────────────────────────────────────────────────
// Only present when the server runs with --workshop. The point of the page is
// the cycle: change the prompt or the fields, run five cards, look at what
// came back, change something else. Types are left to the server — send
// "auto" and the resolved type comes back, so the guess is visible rather
// than something you had to decide up front.

const FIELD_TYPES = ["auto", "text", "number", "decimal", "yes/no", "list"];

async function loadWorkshop() {
  try {
    const res = await fetch("api/workshop/state");
    state.workshop = res.ok ? await res.json() : false;
  } catch {
    state.workshop = false;
  }
  return state.workshop;
}

function fieldRow(f = {}, i = 0) {
  const type = f.type && FIELD_TYPES.includes(f.type) ? f.type : "auto";
  const opts = FIELD_TYPES.map(
    (o) => `<option value="${o}"${o === type ? " selected" : ""}>${o}</option>`,
  ).join("");
  return `<tr data-row="${i}">
    <td><input data-f="name" value="${escapeHtml(f.name ?? "")}" placeholder="field name"></td>
    <td><select data-f="type">${opts}</select></td>
    <td><input data-f="description" value="${escapeHtml(f.description ?? "")}"
        placeholder="optional — a short structural hint"></td>
    <td><button class="button outline small" data-remove="${i}" aria-label="Remove field">✕</button></td>
  </tr>`;
}

function readWorkshopForm() {
  const prompt = document.getElementById("ws-prompt").value;
  const fields = [...document.querySelectorAll("#ws-fields tbody tr")]
    .map((tr) => ({
      name: tr.querySelector('[data-f="name"]').value,
      type: tr.querySelector('[data-f="type"]').value,
      description: tr.querySelector('[data-f="description"]').value,
    }))
    .filter((f) => f.name.trim())
    .map((f) => (f.type === "auto" ? { ...f, type: "" } : f));
  return { prompt, fields };
}

// Said before they authorise, not after: signing in here spends their own
// inference allowance, which is not what "sign in" usually implies. Plain
// numbers rather than reassurance — the cost is small and checkable.
function inferenceNoticeHtml(model) {
  return `
    <div role="alert" data-variant="warning" style="max-width:44rem;">
      <strong>Running the model uses your own Hugging Face inference.</strong>
      <p style="margin:.5rem 0 0;">
        After sign-in each run is billed to your account. By default the space
        uses ${
          model ? `<code>${escapeHtml(model)}</code>` : "a small vision model"
        }, which costs a fraction of a penny. Your token stays in this browser
        tab and is sent with each request — it is never stored on the server.
      </p>
      <p style="margin:.5rem 0 0;">
        Without signing in you can still read the rounds already here, and
        review and correct them.
      </p>
      <div class="controls">
        <button class="button primary small" id="ws-signin">Sign in with Hugging Face</button>
      </div>
    </div>`;
}

function renderWorkshop() {
  const w = state.workshop;
  const signInNeeded = w.needs_token && !hfAuth?.token;
  document.getElementById("view").innerHTML = `
    <h2>Prompt and fields</h2>
    <p class="text-light" style="max-width:44rem;">
      The prompt tells the model what to do; the fields decide what shape the
      answer comes back in. Change either, run a few cards, and compare the new
      round with the last one.
    </p>

    <label for="ws-prompt"><strong>Prompt</strong></label>
    <textarea id="ws-prompt" rows="14" spellcheck="false"
      style="width:100%; max-width:82ch; font-family:var(--font-mono); font-size:.8125rem;"
      >${escapeHtml(w.prompt ?? "")}</textarea>

    <p class="mt-4"><strong>Fields</strong>
      <span class="text-light" style="font-size:.875rem;">
        — leave the type on <code>auto</code> and it is guessed from the name.</span></p>
    <div class="table"><table id="ws-fields">
      <thead><tr><th>Name</th><th>Holds</th><th>Description</th><th></th></tr></thead>
      <tbody>${(w.fields ?? []).map((f, i) => fieldRow(f, i)).join("")}</tbody>
    </table></div>
    <p><button class="button outline small" id="ws-add">+ Add field</button></p>

    <div class="controls">
      <label class="ws-cards">Cards
        <input id="ws-cards" type="number" min="1" max="${w.max_cards ?? 8}"
               value="${w.max_cards ?? 8}">
      </label>
      <button class="button primary" id="ws-run"${signInNeeded ? " disabled" : ""}>Run</button>
    </div>

    ${signInNeeded ? inferenceNoticeHtml(w.model) : ""}

    <div id="ws-status" class="mb-4"></div>

    <div class="controls">
      <button class="button outline small" id="ws-reset">Start over</button>
      <span class="text-light">Throws away your prompt, fields and rounds.</span>
    </div>
  `;

  document.getElementById("ws-add").addEventListener("click", () => {
    const tbody = document.querySelector("#ws-fields tbody");
    tbody.insertAdjacentHTML("beforeend", fieldRow({}, tbody.children.length));
  });
  document.getElementById("ws-fields").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-remove]");
    if (btn) btn.closest("tr").remove();
  });
  document.getElementById("ws-run").addEventListener("click", startWorkshopRun);
  document.getElementById("ws-signin")?.addEventListener("click", async () => {
    await hfSignIn();
    renderWorkshop();   // redraw: the notice goes, Run comes alive
  });
  document.getElementById("ws-reset").addEventListener("click", async () => {
    if (!confirm("Start over? Your prompt, fields and rounds are deleted.")) return;
    await fetch("api/workshop/session", { method: "DELETE" });
    state.workshop = undefined;
    state.datasets = [];
    state.dataset = null;
    await loadWorkshop();
    await loadDatasets();
    // Out to the front page, not back to the editor: starting over means
    // arriving again, and the editor alone would just show the default prompt
    // with nothing to say the rounds had gone too.
    location.hash = "#/select";   // hashchange redraws
  });
}

async function startWorkshopRun() {
  const status = document.getElementById("ws-status");
  const runBtn = document.getElementById("ws-run");
  const { prompt, fields } = readWorkshopForm();
  const cards = Number(document.getElementById("ws-cards").value) || state.workshop.max_cards;

  if (!prompt.trim()) return (status.innerHTML = `<p class="bad">The prompt is empty.</p>`);
  if (!fields.length) return (status.innerHTML = `<p class="bad">Add at least one field.</p>`);

  runBtn.disabled = true;
  status.innerHTML = `<p class="text-light">Starting…</p>`;
  let job;
  try {
    const res = await fetch("api/workshop/run", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        // The run is charged to whoever is signed in. Same token, same header
        // and same per-request handling as a push — the server keeps none.
        ...(hfAuth?.token ? { authorization: `Bearer ${hfAuth.token}` } : {}),
      },
      body: JSON.stringify({ prompt, fields, cards }),
    });
    job = await res.json();
    if (!res.ok) throw new Error(job.error || `run refused (${res.status})`);
  } catch (e) {
    runBtn.disabled = false;
    return (status.innerHTML = `<p class="bad">${escapeHtml(e.message)}</p>`);
  }

  const draw = (j) => {
    status.innerHTML = `
      <progress value="${j.done}" max="${j.total}" style="width:100%; max-width:24rem;"></progress>
      <p class="text-light">${j.done} of ${j.total} card${j.total === 1 ? "" : "s"}${
        j.failures.length ? ` · ${j.failures.length} failed` : ""
      }</p>`;
  };
  draw(job);

  while (job.status === "running") {
    await new Promise((r) => setTimeout(r, 1200));
    try {
      job = await (await fetch(`api/workshop/job/${job.id}`)).json();
    } catch {
      break;
    }
    draw(job);
  }

  runBtn.disabled = false;
  state.workshop.runs_used = (state.workshop.runs_used ?? 0) + 1;

  if (job.status === "error") {
    status.innerHTML = `<p class="bad"><strong>The run failed.</strong> ${escapeHtml(
      job.error,
    )}</p>`;
    return;
  }
  await loadDatasets();

  // A failed card carries the reason the model gave up — a runaway hitting the
  // token cap, or JSON that didn't parse. That is usually the prompt's doing,
  // so it's worth stopping for: navigating straight on would leave a short
  // round and no explanation. A clean run still goes through without a click.
  if (job.failures.length) {
    status.innerHTML = `
      <div role="alert" data-variant="warning">
        <strong>${job.failures.length} of ${job.total} card${
          job.total === 1 ? "" : "s"
        } didn't come back.</strong>
        <ul style="margin:.5rem 0 0; padding-left:1.1rem;">
          ${job.failures.map((f) => `<li>${escapeHtml(f)}</li>`).join("")}
        </ul>
      </div>
      <div class="controls">
        <button class="button primary small" id="ws-go">See the round →</button>
      </div>`;
    document.getElementById("ws-go").addEventListener("click", () => {
      setDataset(job.round);
      location.hash = "#/review";
    });
    return;
  }

  // Straight into the round they just made — the point is to look at it.
  status.innerHTML = `<p class="ok">Done — ${escapeHtml(job.round)} is ready.</p>`;
  setDataset(job.round);
  location.hash = "#/review";
}

// ── Routing ───────────────────────────────────────────────────────────
function currentRoute() {
  if (location.hash === "#/select") return "select";
  if (location.hash === "#/workshop") return "workshop";
  if (location.hash === "#/stats") return "stats";
  if (location.hash === "#/eval" || location.hash.startsWith("#/eval/")) return "eval";
  return "review";
}

function isEval() {
  return currentRoute() === "eval";
}

async function route() {
  if (!state.datasets.length) {
    await loadDatasets();
  }
  // The editor is reached from Results, under the prompt and field history it
  // follows on from — not from the top nav, which is the review path.
  if (state.workshop === undefined) {
    await loadWorkshop();
  }

  // The editor is about what you're going to run, not what has been run, so it
  // sits ahead of dataset resolution — a fresh session may have no rounds yet.
  if (currentRoute() === "workshop" && state.workshop) {
    // Re-read every time. The prompt and fields live on the server and a run
    // rewrites them, so the copy cached at page load is stale the moment they
    // run anything — and the editor would reopen on the default prompt with
    // their version apparently gone.
    await loadWorkshop();
    if (state.workshop) {
      renderHeader();
      renderWorkshop();
      return;
    }
  }

  // Resolve the current dataset:
  // - 0 datasets → handled by renderPicker (shows guidance).
  // - 1 dataset  → auto-select.
  // - 2+ datasets → always show the picker first (no persisted choice).
  if (!state.dataset && state.datasets.length === 1) {
    setDataset(state.datasets[0].name);
  }

  if (currentRoute() === "select" || !state.dataset) {
    renderHeader();
    renderPicker();
    return;
  }

  renderHeader();
  await ensureView();

  if (currentRoute() === "stats") {
    await renderStats();
    return;
  }

  if (currentRoute() === "eval") {
    const m = location.hash.match(/^#\/eval\/(.+)$/);
    const targetId = m ? m[1] : null;
    if (state.samplesMode !== "eval") {
      await loadEvalList(targetId);
    } else if (targetId) {
      const idx = state.samples.findIndex((s) => String(s.id) === String(targetId));
      if (idx !== -1) {
        state.index = idx;
        await loadSample();
      } else renderEditor();
    } else if (state.current) {
      renderEditor();
    } else {
      await loadEvalList(null);
    }
    return;
  }

  const match = location.hash.match(/^#\/review\/(.+)$/);
  const targetId = match ? match[1] : null;
  if (state.samplesMode !== "review" || !state.samples.length) {
    await loadList(targetId);
  } else if (targetId) {
    const idx = state.samples.findIndex((s) => String(s.id) === String(targetId));
    if (idx !== -1) {
      state.index = idx;
      await loadSample();
    } else render();
  } else {
    render();
  }
}

window.addEventListener("hashchange", route);
trackNavHeight();
route();
