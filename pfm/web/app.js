"use strict";

/* Portfolio Manager web UI — no framework, no build step.
 *
 * The server owns every rule (validation, paths, front matter); this file only
 * renders state and calls the JSON API.  All dynamic text goes through
 * textContent; the only innerHTML use is the server-rendered, HTML-escaped
 * Markdown preview.
 */

const state = {
  meta: null,
  entries: [],
  selected: null,
};

// --------------------------------------------------------------------------
// Small helpers
// --------------------------------------------------------------------------

const byId = (id) => document.getElementById(id);

function el(tag, attributes = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key === "html") node.innerHTML = value;
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function option(value, label, selected = false) {
  const node = el("option", { value }, label);
  node.selected = selected;
  return node;
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(path, { ...options, headers });
  if (response.status === 204) return null;

  let payload = null;
  try {
    payload = await response.json();
  } catch (error) {
    payload = null;
  }

  if (!response.ok) {
    const problem = payload && payload.error ? payload.error : {};
    const details = Array.isArray(problem.details) ? problem.details : [];
    const message = problem.message || `HTTP ${response.status}`;
    throw new Error([message, ...details].join(" — "));
  }
  return payload;
}

let toastTimer = null;

function toast(message, kind = "ok") {
  const node = byId("toast");
  node.textContent = message;
  node.className = `toast ${kind}`;
  node.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    node.hidden = true;
  }, 4200);
}

function reportError(error) {
  console.error(error);
  toast(error.message || String(error), "error");
}

// --------------------------------------------------------------------------
// Tabs
// --------------------------------------------------------------------------

function activateView(name) {
  for (const tab of document.querySelectorAll(".tab")) {
    tab.classList.toggle("is-active", tab.dataset.view === name);
  }
  for (const view of document.querySelectorAll(".view")) {
    view.classList.toggle("is-active", view.id === `view-${name}`);
  }
  if (name === "stats") loadStats();
  if (name === "check") runChecks();
}

// --------------------------------------------------------------------------
// Bootstrap: forms built from the server metadata
// --------------------------------------------------------------------------

async function loadMeta() {
  const meta = await api("/api/meta");
  state.meta = meta;

  byId("version").textContent = `v${meta.version}`;
  byId("portfolio-root").textContent = meta.portfolio_root;

  const typeSelect = byId("new-type");
  typeSelect.replaceChildren(
    ...meta.types.map((type) => option(type.value, type.value, type.value === "project")),
  );

  const statusSelect = byId("new-status");
  statusSelect.replaceChildren(
    ...meta.statuses.map((status) => option(status, status, status === "draft")),
  );

  const domainSelect = byId("new-domain");
  domainSelect.replaceChildren(...Object.keys(meta.domains).map((domain) => option(domain, domain)));

  byId("filter-type").replaceChildren(
    option("", "All types"),
    ...meta.types.map((type) => option(type.value, type.value)),
  );
  byId("filter-status").replaceChildren(
    option("", "All statuses"),
    ...meta.statuses.map((status) => option(status, status)),
  );
  byId("filter-domain").replaceChildren(
    option("", "All domains"),
    ...Object.keys(meta.domains).map((domain) => option(domain, domain)),
  );

  syncSubdomains();
  renderExtraFields();
}

function syncSubdomains() {
  const domain = byId("new-domain").value;
  const subdomainSelect = byId("new-subdomain");
  const subdomains = (state.meta && state.meta.domains[domain]) || [];
  subdomainSelect.replaceChildren(...subdomains.map((item) => option(item, item)));
}

function renderExtraFields(values = {}) {
  const type = byId("new-type").value;
  const definition = (state.meta.types || []).find((item) => item.value === type);
  const container = byId("new-extra-fields");
  const fields = definition ? definition.fields : [];

  container.replaceChildren(
    ...fields.map((field) => {
      const label = state.meta.field_labels[field] || field;
      const input = el("input", {
        type: "text",
        id: `field-${field}`,
        value: values[field] || "",
        placeholder: field === "pdf" ? "path/to/file.pdf or https://…" : "https://…",
      });
      return el("label", {}, label, input);
    }),
  );
}

// --------------------------------------------------------------------------
// Entry list
// --------------------------------------------------------------------------

async function loadEntries() {
  const params = new URLSearchParams();
  const type = byId("filter-type").value;
  const status = byId("filter-status").value;
  const domain = byId("filter-domain").value;
  const search = byId("search").value.trim();

  if (type) params.set("type", type);
  if (status) params.set("status", status);
  if (domain) params.set("domain", domain);
  if (search) params.set("q", search);

  const payload = await api(`/api/entries?${params.toString()}`);
  state.entries = payload.entries;
  renderEntryList();
}

function renderEntryList() {
  const list = byId("entry-list");
  if (!state.entries.length) {
    list.replaceChildren(el("li", { class: "empty" }, "No entry matches."));
    return;
  }

  list.replaceChildren(
    ...state.entries.map((entry) =>
      el(
        "li",
        {
          dataset: { id: entry.id },
          class: state.selected === entry.id ? "is-active" : "",
          onclick: () => openEntry(entry.id),
        },
        el("div", { class: "entry-title" }, entry.title || "(untitled)"),
        el(
          "div",
          { class: "entry-meta" },
          el("span", { class: `badge ${entry.status}` }, entry.status || "?"),
          el("span", {}, entry.type || "?"),
          el("span", {}, `${entry.domain}/${entry.subdomain}`),
          el("span", {}, entry.date || "no date"),
          ...entry.tags.map((tag) => el("span", { class: "badge" }, tag)),
        ),
      ),
    ),
  );
}

async function openEntry(id) {
  state.selected = id;
  renderEntryList();
  try {
    const payload = await api(`/api/entries/${encodePath(id)}`);
    renderDetail(payload);
  } catch (error) {
    reportError(error);
  }
}

function encodePath(path) {
  return path.split("/").map(encodeURIComponent).join("/");
}

function renderDetail(payload) {
  const entry = payload.entry;
  const container = byId("entry-detail");

  const rows = Object.entries(entry.metadata).map(([key, value]) => {
    const text = Array.isArray(value) ? value.join(", ") : String(value);
    return el("tr", {}, el("th", {}, key), el("td", {}, text));
  });

  const typeFields = (state.meta.types.find((item) => item.value === entry.type) || {}).fields || [];

  const editInputs = {
    title: el("input", { type: "text", value: entry.title, id: "edit-title" }),
    date: el("input", { type: "text", value: entry.date, id: "edit-date" }),
    tags: el("input", { type: "text", value: entry.tags.join(", "), id: "edit-tags" }),
  };
  for (const field of typeFields) {
    editInputs[field] = el("input", {
      type: "text",
      value: entry.metadata[field] || "",
      id: `edit-field-${field}`,
    });
  }

  const statusSelect = el(
    "select",
    { id: "edit-status" },
    ...state.meta.statuses.map((status) => option(status, status, status === entry.status)),
  );

  container.replaceChildren(
    el(
      "div",
      {},
      el("h2", {}, entry.title || "(untitled)"),
      el(
        "div",
        { class: "entry-meta" },
        el("span", { class: `badge ${entry.status}` }, entry.status),
        el("span", {}, entry.type),
        el("span", {}, `${entry.domain}/${entry.subdomain}`),
        el("span", {}, entry.path),
      ),
    ),
    el("h3", {}, "Metadata"),
    el("table", { class: "meta-table" }, el("tbody", {}, ...rows)),
    el("h3", {}, "Actions"),
    el(
      "div",
      { class: "detail-actions" },
      statusSelect,
      el(
        "button",
        { class: "primary", onclick: () => applyStatus(entry.id, statusSelect.value) },
        "Set status",
      ),
      el(
        "button",
        { class: "danger", onclick: () => deleteEntry(entry.id) },
        "Delete",
      ),
    ),
    el("h3", {}, "Edit"),
    el(
      "div",
      { class: "grid two" },
      el("label", {}, "Title", editInputs.title),
      el("label", {}, "Date", editInputs.date),
      el("label", {}, "Tags (comma separated)", editInputs.tags),
      ...typeFields.map((field) =>
        el("label", {}, state.meta.field_labels[field] || field, editInputs[field]),
      ),
    ),
    el(
      "div",
      { class: "actions" },
      el(
        "button",
        { class: "primary", onclick: () => saveMetadata(entry.id, editInputs, typeFields) },
        "Save metadata",
      ),
    ),
    el("h3", {}, "Preview"),
    el("div", { class: "preview", html: payload.html }),
  );
}

async function applyStatus(id, status) {
  try {
    const payload = await api(`/api/entries/${encodePath(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    toast(`${payload.entry.title}: ${status}`);
    await loadEntries();
    await openEntry(id);
  } catch (error) {
    reportError(error);
  }
}

async function saveMetadata(id, inputs, typeFields) {
  const body = {
    title: inputs.title.value.trim(),
    date: inputs.date.value.trim(),
    tags: inputs.tags.value,
    fields: {},
  };
  for (const field of typeFields) {
    body.fields[field] = inputs[field].value.trim();
  }

  try {
    const payload = await api(`/api/entries/${encodePath(id)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
    toast(`Saved ${payload.entry.title}`);
    await loadEntries();
    await openEntry(id);
  } catch (error) {
    reportError(error);
  }
}

async function deleteEntry(id) {
  if (!window.confirm(`Delete ${id}? This cannot be undone.`)) return;
  try {
    await api(`/api/entries/${encodePath(id)}`, { method: "DELETE" });
    toast("Entry deleted");
    state.selected = null;
    byId("entry-detail").replaceChildren(el("p", { class: "muted" }, "Select an entry."));
    await loadEntries();
  } catch (error) {
    reportError(error);
  }
}

// --------------------------------------------------------------------------
// Creation
// --------------------------------------------------------------------------

async function submitCreate(event) {
  event.preventDefault();
  const status = byId("create-status");
  status.textContent = "Creating…";

  const type = byId("new-type").value;
  const definition = state.meta.types.find((item) => item.value === type);
  const fields = {};
  for (const field of definition ? definition.fields : []) {
    const input = byId(`field-${field}`);
    if (input && input.value.trim()) fields[field] = input.value.trim();
  }

  const body = {
    type,
    title: byId("new-title").value.trim(),
    domain: byId("new-domain").value,
    subdomain: byId("new-subdomain").value,
    tags: byId("new-tags").value,
    date: byId("new-date").value,
    status: byId("new-status").value,
    bundle: byId("new-bundle").checked,
    fields,
  };

  try {
    const payload = await api("/api/entries", { method: "POST", body: JSON.stringify(body) });
    byId("create-form").reset();
    byId("new-date").value = new Date().toISOString().slice(0, 10);
    syncSubdomains();
    renderExtraFields();
    toast(`Created ${payload.entry.path}`);
    await loadEntries();
    await openEntry(payload.entry.id);
    activateView("entries");
  } catch (error) {
    reportError(error);
  } finally {
    status.textContent = "";
  }
}

// --------------------------------------------------------------------------
// Statistics and quality
// --------------------------------------------------------------------------

function statCard(title, value, items = []) {
  const card = el("div", { class: "stat-card" }, el("h3", {}, title));
  card.append(el("div", { class: "stat-value" }, String(value)));
  if (items.length) {
    card.append(el("ul", { class: "stat-list" }, ...items.map((item) => el("li", {}, item))));
  }
  return card;
}

function counterItems(counters) {
  return Object.entries(counters || {}).map(([key, value]) => `${key}: ${value}`);
}

async function loadStats() {
  try {
    const stats = await api("/api/stats");
    const container = byId("stats-content");
    container.replaceChildren(
      statCard("Entries", stats.total),
      statCard("By type", stats.by_type.project ?? 0, counterItems(stats.by_type)),
      statCard("By status", stats.by_status.published ?? 0, counterItems(stats.by_status)),
      statCard("By domain", Object.keys(stats.by_domain).length, counterItems(stats.by_domain)),
      statCard(
        "Top tags",
        stats.top_tags.length,
        stats.top_tags.map((item) => `${item.tag} (${item.count})`),
      ),
      statCard("Published projects", stats.published_projects.length),
      statCard("Publications", stats.publications_with_pdf, [
        `with PDF: ${stats.publications_with_pdf}`,
        `without PDF: ${stats.publications_without_pdf}`,
      ]),
      statCard(
        "To complete",
        stats.incomplete.length,
        stats.incomplete.slice(0, 12).map((item) => `${item.id}: ${item.reasons}`),
      ),
    );
  } catch (error) {
    reportError(error);
  }
}

function renderIssues(report) {
  const container = byId("check-content");
  const issues = [...report.errors, ...report.warnings];

  if (!issues.length) {
    container.replaceChildren(el("p", { class: "muted" }, `All good — ${report.checked} entries checked.`));
    return;
  }

  container.replaceChildren(
    ...issues.map((issue) =>
      el(
        "div",
        { class: `issue ${issue.severity}` },
        el("span", { class: "code" }, issue.code),
        el("strong", {}, issue.path),
        el("div", {}, issue.message),
      ),
    ),
  );
}

async function runChecks() {
  try {
    const report = await api("/api/check", { method: "POST", body: JSON.stringify({}) });
    renderIssues(report);
  } catch (error) {
    reportError(error);
  }
}

async function regenerateIndexes() {
  try {
    const payload = await api("/api/index", {
      method: "POST",
      body: JSON.stringify({ include_drafts: true }),
    });
    toast(`Wrote ${payload.files.length} index page(s)`);
  } catch (error) {
    reportError(error);
  }
}

async function normaliseHugo() {
  try {
    const payload = await api("/api/hugo", { method: "POST", body: JSON.stringify({ apply: true }) });
    toast(`Normalised ${payload.changed.length} entry(ies), ${payload.errors.length} error(s)`);
    await loadEntries();
  } catch (error) {
    reportError(error);
  }
}

// --------------------------------------------------------------------------
// Wiring
// --------------------------------------------------------------------------

function wireEvents() {
  for (const tab of document.querySelectorAll(".tab")) {
    tab.addEventListener("click", () => activateView(tab.dataset.view));
  }

  byId("filter-type").addEventListener("change", loadEntries);
  byId("filter-status").addEventListener("change", loadEntries);
  byId("filter-domain").addEventListener("change", loadEntries);
  byId("refresh").addEventListener("click", loadEntries);

  let searchTimer = null;
  byId("search").addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(loadEntries, 220);
  });

  byId("new-type").addEventListener("change", () => renderExtraFields());
  byId("new-domain").addEventListener("change", syncSubdomains);
  byId("create-form").addEventListener("submit", submitCreate);

  byId("reload-stats").addEventListener("click", loadStats);
  byId("write-stats").addEventListener("click", async () => {
    try {
      const payload = await api("/api/stats", { method: "POST", body: JSON.stringify({}) });
      toast(`Written: ${payload.written}`);
    } catch (error) {
      reportError(error);
    }
  });

  byId("run-check").addEventListener("click", runChecks);
  byId("run-index").addEventListener("click", regenerateIndexes);
  byId("run-hugo").addEventListener("click", normaliseHugo);
}

async function start() {
  byId("new-date").value = new Date().toISOString().slice(0, 10);
  wireEvents();
  try {
    await loadMeta();
    await loadEntries();
  } catch (error) {
    reportError(error);
  }
}

document.addEventListener("DOMContentLoaded", start);
