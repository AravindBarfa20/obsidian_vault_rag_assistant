"use strict";

const state = {
  history: [],
  busy: false,
  sources: [],
  indexState: "ready",
  indexPoll: null,
};

const el = {
  healthPill: document.querySelector("#health-pill"),
  healthLabel: document.querySelector("#health-label"),
  heroNotes: document.querySelector("#hero-notes"),
  heroChunks: document.querySelector("#hero-chunks"),
  sourceCount: document.querySelector("#source-count"),
  sourceList: document.querySelector("#source-list"),
  sourceSearch: document.querySelector("#source-search"),
  refreshSources: document.querySelector("#refresh-sources"),
  reindexButton: document.querySelector("#reindex-button"),
  messages: document.querySelector("#messages"),
  welcome: document.querySelector("#welcome-note"),
  form: document.querySelector("#query-form"),
  input: document.querySelector("#question-input"),
  askButton: document.querySelector("#ask-button"),
  clearChat: document.querySelector("#clear-chat"),
  modelLabel: document.querySelector("#model-label"),
  toast: document.querySelector("#toast"),
  indexingNote: document.querySelector("#indexing-note"),
  indexingTitle: document.querySelector("#indexing-title"),
  indexingMessage: document.querySelector("#indexing-message"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  let payload = null;
  try { payload = await response.json(); } catch { /* response may be empty */ }
  if (!response.ok) {
    const error = new Error(payload?.error || `Request failed (${response.status})`);
    error.code = payload?.code;
    error.status = response.status;
    throw error;
  }
  return payload;
}

function showToast(message) {
  el.toast.textContent = message;
  el.toast.classList.add("visible");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => el.toast.classList.remove("visible"), 3600);
}

async function loadHealth() {
  try {
    const health = await api("/health");
    applyIndexState(health);
    el.heroChunks.textContent = `${health.indexed_chunks} passages`;
  } catch {
    el.healthPill.className = "health-pill offline";
    el.healthLabel.textContent = "API unavailable";
  }
}

function updateQueryControls() {
  const unavailable = state.busy || state.indexState === "indexing";
  el.askButton.disabled = unavailable;
  el.input.disabled = unavailable;
  document.querySelectorAll("[data-question]").forEach((button) => {
    button.disabled = unavailable;
  });
}

function scheduleIndexPoll() {
  clearTimeout(state.indexPoll);
  if (state.indexState !== "indexing") return;
  state.indexPoll = setTimeout(() => loadHealth(), 2500);
}

function applyIndexState(health) {
  const previous = state.indexState;
  state.indexState = health.index_state || "ready";
  const indexing = state.indexState === "indexing";
  const failed = state.indexState === "failed";

  el.healthPill.className = `health-pill ${failed ? "offline" : "online"}`;
  el.healthLabel.textContent = indexing
    ? "Preparing library"
    : failed
      ? "Index needs attention"
      : health.gemini_configured ? "Ready" : "Demo mode";
  el.modelLabel.textContent = indexing
    ? "Indexing your vault in the background"
    : "Answers grounded in indexed notes";
  el.input.placeholder = indexing
    ? "Your notes are being prepared…"
    : "Ask a question about your notes…";
  el.indexingNote.hidden = !indexing && !failed;
  el.indexingNote.classList.toggle("failed", failed);
  el.indexingTitle.textContent = failed ? "The vault needs a refresh" : "Indexing your field notes";
  el.indexingMessage.textContent = failed
    ? "The library could not be prepared automatically. Use Refresh vault index to try again."
    : "Retrieving structure and embedding passages. This usually takes under a minute.";
  el.reindexButton.disabled = indexing;
  el.refreshSources.disabled = indexing;
  el.sourceSearch.disabled = indexing;
  updateQueryControls();
  renderSourceList();
  scheduleIndexPoll();

  if (previous === "indexing" && state.indexState === "ready") {
    loadSources({ announce: true });
    showToast("Your vault is ready to explore.");
  }
}

function renderSourceList() {
  const query = el.sourceSearch.value.trim().toLocaleLowerCase();
  const visibleSources = query
    ? state.sources.filter((source) => {
        const searchable = [source.title, source.source, source.path, source.tags]
          .filter(Boolean)
          .join(" ")
          .toLocaleLowerCase();
        return searchable.includes(query);
      })
    : state.sources;

  el.sourceList.replaceChildren();

  if (!visibleSources.length) {
    const empty = document.createElement("p");
    empty.className = "source-empty";
    empty.textContent = state.sources.length
      ? "No notes match this filter."
      : state.indexState === "indexing"
        ? "Notes will appear here as indexing completes."
        : "No notes indexed yet.";
    el.sourceList.append(empty);
    return;
  }

  visibleSources.forEach((source) => {
    const item = document.createElement("article");
    item.className = "source-item";
    const title = document.createElement("div");
    title.className = "source-title";
    const name = document.createElement("span");
    name.textContent = source.title || source.source;
    const chunks = document.createElement("span");
    chunks.textContent = `${source.chunks} ${source.chunks === 1 ? "passage" : "passages"}`;
    title.append(name, chunks);
    const descriptor = document.createElement("div");
    descriptor.className = "source-descriptor";
    const tags = (source.tags || "")
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean)
      .slice(0, 3);
    descriptor.textContent = tags.length ? tags.map((tag) => `#${tag}`).join("  ") : "Markdown note";
    item.append(title, descriptor);
    el.sourceList.append(item);
  });
}

function renderSources(data) {
  state.sources = data.notes || [];
  el.sourceCount.textContent = data.total_notes;
  el.heroNotes.textContent = `${data.total_notes} notes`;
  el.heroChunks.textContent = `${data.total_chunks} passages`;
  renderSourceList();
}

async function loadSources({ announce = false } = {}) {
  el.refreshSources.classList.add("spinning");
  try {
    renderSources(await api("/sources"));
    if (announce) showToast("Library refreshed.");
  } catch (error) {
    showToast(error.message);
  } finally {
    el.refreshSources.classList.remove("spinning");
  }
}

function addUserMessage(text) {
  const article = document.createElement("article");
  article.className = "message message-user";
  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = "You";
  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = text;
  article.append(label, body);
  el.messages.append(article);
}

function makeCitationButton(index, sources, messageId) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "citation-ref";
  button.textContent = `[S${index}]`;
  button.setAttribute("aria-label", `Open source ${index}: ${sources[index - 1]?.title || "note"}`);
  button.addEventListener("click", () => {
    const card = document.querySelector(`#${messageId}-source-${index}`);
    if (!card) return;
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    card.classList.add("highlight");
    setTimeout(() => card.classList.remove("highlight"), 1400);
  });
  return button;
}

function appendInlineFormatting(container, text, sources, messageId) {
  const tokenPattern = /(\[S\d+\]|\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*)/g;
  let cursor = 0;
  let match;
  while ((match = tokenPattern.exec(text)) !== null) {
    container.append(document.createTextNode(text.slice(cursor, match.index)));
    const token = match[0];
    const citation = token.match(/^\[S(\d+)\]$/);
    if (citation && sources[Number(citation[1]) - 1]) {
      container.append(makeCitationButton(Number(citation[1]), sources, messageId));
    } else if (token.startsWith("**")) {
      const strong = document.createElement("strong");
      strong.textContent = token.slice(2, -2);
      container.append(strong);
    } else if (token.startsWith("`")) {
      const code = document.createElement("code");
      code.textContent = token.slice(1, -1);
      container.append(code);
    } else if (token.startsWith("*")) {
      const emphasis = document.createElement("em");
      emphasis.textContent = token.slice(1, -1);
      container.append(emphasis);
    } else {
      container.append(document.createTextNode(token));
    }
    cursor = match.index + match[0].length;
  }
  container.append(document.createTextNode(text.slice(cursor)));
}

function appendRichAnswer(container, text, sources, messageId) {
  const lines = text.split(/\r?\n/);
  let list = null;
  let listType = null;
  let paragraph = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const node = document.createElement("p");
    appendInlineFormatting(node, paragraph.join(" ").trim(), sources, messageId);
    container.append(node);
    paragraph = [];
  };
  const closeList = () => { list = null; listType = null; };

  lines.forEach((line) => {
    const unordered = line.match(/^\s*[-*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (unordered || ordered) {
      flushParagraph();
      const nextType = ordered ? "ol" : "ul";
      if (!list || listType !== nextType) {
        list = document.createElement(nextType);
        listType = nextType;
        container.append(list);
      }
      const item = document.createElement("li");
      appendInlineFormatting(item, (unordered || ordered)[1], sources, messageId);
      list.append(item);
    } else if (!line.trim()) {
      flushParagraph();
      closeList();
    } else {
      closeList();
      paragraph.push(line.trim());
    }
  });
  flushParagraph();
}

function citedSourceIndices(answer, sourceCount) {
  const indices = [];
  const pattern = /\[S(\d+)\]/g;
  let match;
  while ((match = pattern.exec(answer)) !== null) {
    const index = Number(match[1]);
    if (index > 0 && index <= sourceCount && !indices.includes(index)) indices.push(index);
  }
  return indices;
}

function addAssistantMessage(result) {
  const messageId = `answer-${Date.now()}`;
  const article = document.createElement("article");
  article.className = `message message-assistant${result.grounded ? "" : " ungrounded"}${result.error ? " service-error" : ""}`;
  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = result.error
    ? "Service temporarily unavailable"
    : result.grounded
      ? "Fieldnotes"
      : "No supporting note found";
  const body = document.createElement("div");
  body.className = "message-body";
  appendRichAnswer(body, result.answer, result.sources || [], messageId);
  article.append(label, body);

  const citedIndices = citedSourceIndices(result.answer, result.sources?.length || 0);
  if (citedIndices.length) {
    const evidenceHeading = document.createElement("div");
    evidenceHeading.className = "evidence-heading";
    evidenceHeading.textContent = `${citedIndices.length} cited ${citedIndices.length === 1 ? "passage" : "passages"}`;
    article.append(evidenceHeading);
    const grid = document.createElement("div");
    grid.className = "citation-grid";
    citedIndices.forEach((sourceIndex) => {
      const source = result.sources[sourceIndex - 1];
      const card = document.createElement("article");
      card.className = "citation-card";
      card.id = `${messageId}-source-${sourceIndex}`;
      const top = document.createElement("div");
      top.className = "citation-top";
      const name = document.createElement("span");
      name.textContent = `[S${sourceIndex}] ${source.title || source.source}`;
      const evidenceLabel = document.createElement("span");
      evidenceLabel.textContent = "Cited evidence";
      top.append(name, evidenceLabel);
      const section = document.createElement("div");
      section.className = "citation-section";
      section.textContent = source.section || source.path;
      const snippet = document.createElement("div");
      snippet.className = "citation-snippet";
      appendRichAnswer(snippet, source.snippet, [], `${messageId}-evidence-${sourceIndex}`);
      card.append(top, section, snippet);
      grid.append(card);
    });
    article.append(grid);
  }

  const meta = document.createElement("div");
  meta.className = "answer-meta";
  meta.textContent = result.error
    ? "Your question was not processed"
    : result.grounded
      ? "Generated only from the cited notes above"
      : "No indexed passage cleared the evidence threshold";
  article.append(meta);
  el.messages.append(article);
}

function addThinking() {
  const row = document.createElement("div");
  row.className = "message thinking";
  row.id = "thinking";
  const dots = document.createElement("span");
  dots.className = "thinking-dots";
  dots.append(document.createElement("i"), document.createElement("i"), document.createElement("i"));
  const text = document.createElement("span");
  text.textContent = "Searching the indexed notes…";
  row.append(dots, text);
  el.messages.append(row);
}

function setBusy(busy) {
  state.busy = busy;
  updateQueryControls();
  el.askButton.querySelector("span").textContent = busy ? "Reading" : "Ask";
}

function scrollToLatest() {
  requestAnimationFrame(() => { el.messages.scrollTop = el.messages.scrollHeight; });
}

async function ask(question) {
  const clean = question.trim();
  if (!clean || state.busy) return;
  el.welcome?.remove();
  el.clearChat.disabled = false;
  addUserMessage(clean);
  addThinking();
  el.input.value = "";
  autoSizeInput();
  setBusy(true);
  scrollToLatest();

  try {
    const result = await api("/query", {
      method: "POST",
      body: JSON.stringify({ question: clean, history: state.history.slice(-6), top_k: 6 }),
    });
    document.querySelector("#thinking")?.remove();
    addAssistantMessage(result);
    state.history.push(
      { role: "user", content: clean },
      { role: "assistant", content: result.answer },
    );
  } catch (error) {
    document.querySelector("#thinking")?.remove();
    const rateLimited = error.status === 429 || /quota|resource_exhausted/i.test(error.message);
    const providerBusy = /503|unavailable|high demand/i.test(error.message);
    addAssistantMessage({
      answer: rateLimited
        ? "The answer service is busy right now. Please wait a minute and try again."
        : providerBusy
          ? "The answer service is handling unusually high demand. Your vault is ready; please try your question again in a moment."
        : "The answer service is temporarily unavailable. Please try again shortly.",
      grounded: false,
      sources: [],
      query_used: clean,
      model: "System",
      error: true,
    });
  } finally {
    setBusy(false);
    el.input.focus();
    scrollToLatest();
  }
}

function autoSizeInput() {
  el.input.style.height = "auto";
  el.input.style.height = `${Math.min(el.input.scrollHeight, 150)}px`;
}

el.form.addEventListener("submit", (event) => {
  event.preventDefault();
  ask(el.input.value);
});
el.input.addEventListener("input", autoSizeInput);
el.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    el.form.requestSubmit();
  }
});
document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => ask(button.dataset.question));
});
el.clearChat.addEventListener("click", () => {
  state.history = [];
  el.messages.replaceChildren(el.welcome);
  el.clearChat.disabled = true;
  showToast("Conversation cleared.");
  el.input.focus();
});
el.refreshSources.addEventListener("click", () => loadSources({ announce: true }));
el.sourceSearch.addEventListener("input", renderSourceList);
el.reindexButton.addEventListener("click", async () => {
  el.reindexButton.disabled = true;
  el.reindexButton.querySelector("span").textContent = "Refreshing index…";
  try {
    const report = await api("/ingest", { method: "POST", body: JSON.stringify({ force: false }) });
    await loadSources();
    const removed = report.notes_deleted ? `; ${report.notes_deleted} removed` : "";
    showToast(`${report.notes_ingested} changed notes indexed${removed}; ${report.notes_skipped_unchanged} unchanged.`);
  } catch (error) {
    showToast(error.message);
  } finally {
    el.reindexButton.disabled = false;
    el.reindexButton.querySelector("span").textContent = "Refresh vault index";
  }
});

Promise.all([loadHealth(), loadSources()]);
