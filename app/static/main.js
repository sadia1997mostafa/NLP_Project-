const form = document.getElementById("query-form");
const query = document.getElementById("query");
const submit = document.getElementById("submit-button");
const clear = document.getElementById("clear-button");
const count = document.getElementById("character-count");
const status = document.getElementById("service-status");
const result = document.getElementById("result");
const thinkingPanel = document.getElementById("thinking-panel");
const topicForm = document.getElementById("topic-form");
const topicService = document.getElementById("topic-service");
const topicChoice = document.getElementById("topic-choice");
const topicSubmit = document.getElementById("topic-submit");
const changeTopic = document.getElementById("change-topic");
const historyList = document.getElementById("history-list");
const historyEmpty = document.getElementById("history-empty");
const clearHistory = document.getElementById("clear-history");
const historyKey = "nagoriksheba.recentQuestions.v3";
const legacyHistoryKeys = ["nagoriksheba.recentQuestions.v1", "nagoriksheba.recentQuestions.v2"];
const historyLimit = 8;
const progressStages = ["privacy", "service", "parent", "intent", "grounding", "answer_generation"];

let catalog = [];
let catalogError = false;
let lastPrivacyWarnings = [];
let lastMaskedQuestion = "";
let suggestedService = "";
let responseLanguage = "en";
let isSubmitting = false;
let isComposing = false;
let progressEventLog = [];

const serviceNames = {
  NID: "National ID",
  BIRTH_REGISTRATION: "Birth registration",
  PASSPORT: "Passport",
  TAX: "Tax",
  POLICE_GD: "Police general diary",
  DRIVING_LICENCE: "Driving licence",
};

const privacyNames = {
  nid: "National ID",
  phone: "phone number",
  email: "email address",
  otp: "one-time password",
  password: "password",
  address: "address",
  bank_account: "bank account",
  birth_registration: "birth registration number",
  passport: "passport number",
  tin: "TIN",
  driving_licence: "driving licence number",
  application_id: "application/reference ID",
  date_of_birth: "date of birth",
  identifier: "identifier",
  payment_card: "payment card",
};

function setText(id, value) {
  document.getElementById(id).textContent = value || "";
}

function setVisible(id, visible) {
  document.getElementById(id).hidden = !visible;
}

function humanizeIdentifier(value) {
  if (!value) return "Not resolved";
  return String(value)
    .replace(/^(NID|BIRTH_REGISTRATION|PASSPORT|TAX|POLICE_GD|DRIVING_LICENCE)_/, "")
    .split("_")
    .filter(Boolean)
    .map(word => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
}

function percent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  return `${Math.round(Math.max(0, Math.min(1, number)) * 100)}%`;
}

function readHistory() {
  try {
    for (const key of legacyHistoryKeys) sessionStorage.removeItem(key);
    const stored = JSON.parse(sessionStorage.getItem(historyKey) || "[]");
    return Array.isArray(stored)
      ? stored.filter(item => item && typeof item.question === "string").slice(0, historyLimit)
      : [];
  } catch (_) {
    return [];
  }
}

let recentQuestions = readHistory();

function renderMaskedText(container, text) {
  container.replaceChildren();
  for (const part of String(text || "").split(/(\[[A-Z_]+\])/g).filter(Boolean)) {
    const span = document.createElement("span");
    span.textContent = part;
    if (/^\[[A-Z_]+\]$/.test(part)) span.className = "masked-token";
    container.appendChild(span);
  }
}

function writeHistory() {
  try {
    sessionStorage.setItem(historyKey, JSON.stringify(recentQuestions));
  } catch (_) {
    // The app remains usable when browser storage is unavailable.
  }
}

function renderHistory() {
  historyList.replaceChildren();
  historyEmpty.hidden = recentQuestions.length > 0;
  historyList.hidden = recentQuestions.length === 0;
  clearHistory.hidden = recentQuestions.length === 0;
  for (const entry of recentQuestions) {
    const item = document.createElement("li");
    item.className = "history-item";
    const button = document.createElement("button");
    button.type = "button";
    button.title = "Use this protected question";
    const questionText = document.createElement("span");
    questionText.className = "history-question";
    renderMaskedText(questionText, entry.question);
    const meta = document.createElement("span");
    meta.className = "history-meta";
    const service = document.createElement("span");
    service.textContent = serviceNames[entry.service] || entry.service || "Unconfirmed";
    const time = document.createElement("span");
    time.textContent = new Intl.DateTimeFormat([], { hour: "2-digit", minute: "2-digit" })
      .format(new Date(entry.createdAt));
    meta.appendChild(service);
    meta.appendChild(time);
    button.appendChild(questionText);
    button.appendChild(meta);
    button.addEventListener("click", () => {
      query.value = entry.question;
      updateComposer();
      result.hidden = true;
      query.focus();
    });
    item.appendChild(button);
    historyList.appendChild(item);
  }
}

function rememberQuestion(payload) {
  const protectedQuestion = String(payload.safe_text || "").trim();
  if (!protectedQuestion) return;
  const understanding = payload.understanding || {};
  recentQuestions = recentQuestions.filter(item => item.question !== protectedQuestion);
  recentQuestions.unshift({
    question: protectedQuestion,
    service: understanding.service || "",
    topic: payload.response?.title || "",
    createdAt: Date.now(),
  });
  recentQuestions = recentQuestions.slice(0, historyLimit);
  writeHistory();
  renderHistory();
}

function addOption(select, label, value) {
  const option = document.createElement("option");
  option.textContent = label;
  option.value = value;
  select.appendChild(option);
}

function showTopics(service = "") {
  topicForm.hidden = false;
  topicService.replaceChildren();
  addOption(topicService, "Select a service", "");
  for (const [serviceId, name] of Object.entries(serviceNames)) addOption(topicService, name, serviceId);
  topicService.value = serviceNames[service] ? service : "";
  updateTopicChoices();
}

function updateTopicChoices() {
  topicChoice.replaceChildren();
  addOption(topicChoice, "Select a topic", "");
  for (const [index, item] of catalog.entries()) {
    if (item.service === topicService.value) {
      const prefix = item.query_topic_id ? "" : item.parent_topic_id ? "General: " : "Overview: ";
      addOption(topicChoice, `${prefix}${item.title}`, String(index));
    }
  }
  topicChoice.value = "";
  topicSubmit.disabled = true;
  setText("topic-error", catalogError ? "Topics are unavailable right now." : "");
  setVisible("topic-error", catalogError);
}

function showResult(state, title, body, kicker) {
  thinkingPanel.hidden = true;
  thinkingPanel.setAttribute?.("aria-busy", "false");
  result.hidden = false;
  result.className = `result ${state}`;
  setText("result-title", title);
  setVisible("result-title", Boolean(title));
  setText("result-body", body);
  setText("result-kicker", kicker);
  setVisible("result-kicker", Boolean(kicker));
  setVisible("scope-note", false);
  setVisible("privacy-notice", false);
  setVisible("masked-preview", false);
  document.getElementById("masked-question").replaceChildren();
  setVisible("result-source", false);
  setVisible("result-meta", false);
  setVisible("language-note", false);
  setVisible("pipeline-panel", false);
  topicForm.hidden = true;
  changeTopic.hidden = true;
  setVisible("result-steps", false);
  document.getElementById("step-list").replaceChildren();
  setVisible("result-documents", false);
  document.getElementById("document-list").replaceChildren();
}

function showPipeline(payload) {
  const understanding = payload.understanding;
  const answer = payload.response;
  if (!understanding || !answer) return;

  const privacyDetail = payload.privacy_present
    ? `Protected: ${(payload.privacy_types || []).map(type => privacyNames[type] || humanizeIdentifier(type)).join(", ") || "personal information"}`
    : "No sensitive information detected";
  setText("trace-privacy", privacyDetail);

  const service = serviceNames[understanding.service] || humanizeIdentifier(understanding.service);
  const routingMethod = understanding.service_routing === "lexical_anchor"
    ? "explicit wording"
    : understanding.service_routing === "user_selected"
      ? "selected by user"
      : understanding.service_resolution === "explicit_name_correction"
        ? "explicit wording correction"
        : "local classifier";
  setText("trace-service", `${service} · ${routingMethod}`);
  setText("trace-parent", understanding.parent_topic || humanizeIdentifier(understanding.parent_topic_id));
  setText("trace-intent", understanding.query_topic || humanizeIdentifier(understanding.query_topic_id));

  const matchLabels = {
    query_topic: "Exact intent guidance",
    parent_topic: "General topic guidance",
    service: "Service overview",
  };
  const matchLevel = answer.match_level || payload.retrieval?.match_level;
  const topicLabel = matchLabels[matchLevel] || "Topic not confirmed";
  const topicScore = understanding.topic_match_score ?? understanding.parent_match_score;
  setText("trace-topic", topicScore == null ? topicLabel : `${topicLabel} · ${percent(topicScore)} match`);

  const basisLabels = {
    local_finetuned_model: "Local Qwen · grounded and quality-checked",
    curated_source_facts: "Controlled response · verified facts",
    exact_intent_answer_plan: "Controlled response · exact answer plan",
  };
  setText("trace-answer", basisLabels[answer.answer_basis] || "Controlled response");
  setText("grounding-status", answer.answer_basis === "local_finetuned_model"
    ? "Qwen + verified facts"
    : answer.answer_basis === "exact_intent_answer_plan"
      ? "Verified answer plan"
      : "Verified guidance");

  setText("service-confidence", percent(understanding.service_confidence) || "Not scored");
  setText("parent-confidence", percent(understanding.parent_confidence) || "Not scored");
  setText("intent-confidence", percent(understanding.intent_confidence ?? understanding.query_topic_confidence) || "Not scored");
  setText("routing-confidence", percent(understanding.overall_confidence ?? understanding.service_confidence) || "Not scored");
  setText("topic-confidence", percent(topicScore) || "Not scored");
  setText("coverage-level", topicLabel);
  setVisible("pipeline-panel", true);
}

function showPayload(payload) {
  const answer = payload.response;
  if (!answer || typeof answer.body !== "string") throw new Error("Malformed response");
  responseLanguage = answer.language || responseLanguage;
  const bengali = responseLanguage === "bn";
  const labels = {
    answer: bengali ? "নির্দেশনা" : "Guidance",
    clarification: bengali ? "আরও তথ্য প্রয়োজন" : "Needs clarification",
    unavailable: bengali ? "নির্দেশনা পাওয়া যায়নি" : "Guidance unavailable",
  };
  showResult(answer.state, answer.title, answer.body, labels[answer.state] || "Result");
  document.documentElement.lang = responseLanguage;
  setText("steps-heading", bengali ? "যাচাইকৃত নির্দেশনা" : "Verified guidance");
  setText("documents-heading", bengali ? "প্রয়োজনীয় নথি ও তথ্য" : "Documents and details");
  setText("source-label", bengali ? "সরকারি উৎস" : "Official source");
  if (answer.language_note) {
    setText("language-note", answer.language_note);
    setVisible("language-note", true);
  }
  suggestedService = payload.understanding?.service || suggestedService;
  if (answer.state !== "answer" || answer.match_level !== "query_topic") showTopics(suggestedService);
  else changeTopic.hidden = false;

  if (answer.state === "answer" && answer.steps?.length) {
    const list = document.getElementById("step-list");
    for (const step of answer.steps) {
      const item = document.createElement("li");
      item.textContent = step;
      list.appendChild(item);
    }
    setVisible("result-steps", true);
  }
  if (answer.state === "answer" && answer.required_documents?.length) {
    const list = document.getElementById("document-list");
    for (const documentText of answer.required_documents) {
      const item = document.createElement("li");
      item.textContent = documentText;
      list.appendChild(item);
    }
    setVisible("result-documents", true);
  }
  if (answer.scope_note && answer.answer_basis !== "local_finetuned_model") {
    setText("scope-note", answer.scope_note);
    setVisible("scope-note", true);
  }
  if (payload.privacy_present) lastPrivacyWarnings = payload.warnings || [];
  if (payload.privacy_present && payload.safe_text) lastMaskedQuestion = payload.safe_text;
  if (lastPrivacyWarnings.length) {
    setText("privacy-message", lastPrivacyWarnings.join(" "));
    setVisible("privacy-notice", true);
    if (lastMaskedQuestion) {
      renderMaskedText(document.getElementById("masked-question"), lastMaskedQuestion);
      setVisible("masked-preview", true);
    }
  }
  if (answer.source) {
    const link = document.getElementById("source-link");
    const url = new URL(answer.source.url);
    if (url.protocol === "https:" && (url.hostname === "gov.bd" || url.hostname.endsWith(".gov.bd"))) {
      link.href = url.href;
      link.textContent = `${answer.source.name} · Open official source ↗`;
      setText("source-date", answer.source.last_verified ? `Reviewed ${answer.source.last_verified}` : "");
      setVisible("result-source", true);
    }
  }
  if (payload.understanding) {
    const understanding = payload.understanding;
    setText("service-name", serviceNames[understanding.service] || humanizeIdentifier(understanding.service));
    setText("topic-name", understanding.query_topic || answer.title);
    setText("priority-name", understanding.priority ? `${understanding.priority} priority` : "");
    setVisible("result-meta", true);
  }
  showPipeline(payload);
  result.focus?.({ preventScroll: true });
  result.scrollIntoView?.({ behavior: "smooth", block: "start" });
}

function resetProgress() {
  progressEventLog = [];
  for (const stage of progressStages) {
    document.getElementById(`progress-${stage}`).className = "progress-step pending";
    setText(`progress-${stage}-value`, "Waiting");
    setText(`progress-${stage}-confidence`, "");
  }
  setText("progress-announcement", "Understanding your request");
}

function activateProgress(stage, label = "Working…") {
  const element = document.getElementById(`progress-${stage}`);
  if (!element || element.className.includes("complete")) return;
  element.className = "progress-step active";
  setText(`progress-${stage}-value`, label);
}

function completeProgress(stage, label, confidence) {
  const element = document.getElementById(`progress-${stage}`);
  if (!element) return;
  element.className = "progress-step complete";
  setText(`progress-${stage}-value`, label);
  setText(`progress-${stage}-confidence`, percent(confidence));
  setText("progress-announcement", `${stage.replace("_", " ")} complete: ${label}`);
  const index = progressStages.indexOf(stage);
  if (index >= 0 && index + 1 < progressStages.length) activateProgress(progressStages[index + 1]);
}

function failProgress(message) {
  const active = progressStages.find(stage => document.getElementById(`progress-${stage}`).className.includes("active"));
  if (active) {
    document.getElementById(`progress-${active}`).className = "progress-step error";
    setText(`progress-${active}-value`, "Could not complete");
  }
  setText("progress-announcement", message);
}

function handleProgressEvent(event, data) {
  progressEventLog.push({ event, data });
  if (event === "started") {
    resetProgress();
    activateProgress("privacy", "Checking for personal information…");
    return;
  }
  if (event === "privacy") {
    const label = data.privacy_present ? "Personal information protected" : "No sensitive information detected";
    completeProgress("privacy", label);
  } else if (event === "service") {
    completeProgress("service", data.display_name || serviceNames[data.label] || humanizeIdentifier(data.label), data.confidence);
  } else if (event === "parent") {
    completeProgress("parent", data.display_name || humanizeIdentifier(data.label), data.confidence);
  } else if (event === "intent") {
    completeProgress("intent", data.display_name || humanizeIdentifier(data.label), data.confidence);
  } else if (event === "grounding") {
    const levels = { query_topic: "Exact intent guidance matched", parent_topic: "Topic guidance matched", service: "Service guidance matched" };
    completeProgress("grounding", levels[data.match_level] || (data.status === "ood" ? "Clarification needed" : "Guidance checked"));
  } else if (event === "answer_generation") {
    completeProgress("answer_generation", data.mode === "local_qwen" ? "Preparing a grounded local answer" : "Preparing verified guidance");
  } else if (event === "error") {
    failProgress(data.message || "Request failed");
  }
}

function parseEventBlock(block) {
  let event = "message";
  const dataLines = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (!dataLines.length) return null;
  return { event, data: JSON.parse(dataLines.join("\n")) };
}

async function streamAnalysis(text, onEvent) {
  const response = await fetch("/api/query/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
    body: JSON.stringify({ text }),
    cache: "no-store",
  });
  if (!response.ok || !response.body?.getReader) throw new Error("Service unavailable");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalPayload = null;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() || "";
    for (const block of blocks) {
      if (!block.trim()) continue;
      const parsed = parseEventBlock(block);
      if (!parsed) continue;
      onEvent(parsed.event, parsed.data);
      if (parsed.event === "complete") finalPayload = parsed.data;
      if (parsed.event === "error") throw new Error(parsed.data.message || "Service unavailable");
    }
    if (done) break;
  }
  if (!finalPayload) throw new Error("Incomplete response");
  return finalPayload;
}

function updateComposer() {
  count.textContent = `${query.value.length} / 4000`;
  if (query.style) {
    query.style.height = "auto";
    query.style.height = `${Math.min(Math.max(query.scrollHeight || 112, 112), 280)}px`;
  }
}

topicService.addEventListener("change", updateTopicChoices);
changeTopic.addEventListener("click", () => { showTopics(suggestedService); changeTopic.hidden = true; });
topicChoice.addEventListener("change", () => { topicSubmit.disabled = !topicChoice.value; });

topicForm.addEventListener("submit", async event => {
  event.preventDefault();
  const item = catalog[Number(topicChoice.value)];
  if (!item || item.service !== topicService.value) return;
  topicSubmit.disabled = true;
  setVisible("topic-error", false);
  try {
    const response = await fetch("/api/guidance", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service: item.service, parent_topic_id: item.parent_topic_id, query_topic_id: item.query_topic_id, language: responseLanguage }),
      cache: "no-store",
    });
    if (!response.ok) throw new Error("Guidance unavailable");
    showPayload(await response.json());
  } catch (_) {
    setText("topic-error", "Selected guidance is unavailable right now.");
    setVisible("topic-error", true);
  } finally {
    topicSubmit.disabled = false;
  }
});

query.addEventListener("input", updateComposer);
query.addEventListener("compositionstart", () => { isComposing = true; });
query.addEventListener("compositionend", () => { isComposing = false; });
query.addEventListener("keydown", event => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing || isComposing) return;
  event.preventDefault();
  if (!isSubmitting) form.requestSubmit();
});

clear.addEventListener("click", () => {
  if (isSubmitting) return;
  query.value = "";
  updateComposer();
  result.hidden = true;
  lastPrivacyWarnings = [];
  lastMaskedQuestion = "";
  suggestedService = "";
  responseLanguage = "en";
  thinkingPanel.hidden = true;
  query.focus();
});

clearHistory.addEventListener("click", () => {
  recentQuestions = [];
  try { sessionStorage.removeItem(historyKey); } catch (_) { /* restricted storage */ }
  renderHistory();
});

form.addEventListener("submit", async event => {
  event.preventDefault();
  const text = query.value.trim();
  if (!text || isSubmitting) return;
  isSubmitting = true;
  submit.disabled = true;
  clear.disabled = true;
  submit.querySelector?.("span") && (submit.querySelector("span").textContent = "Working…");
  lastPrivacyWarnings = [];
  lastMaskedQuestion = "";
  suggestedService = "";
  responseLanguage = "en";
  result.hidden = true;
  resetProgress();
  thinkingPanel.hidden = false;
  thinkingPanel.setAttribute?.("aria-busy", "true");
  try {
    const payload = await streamAnalysis(text, handleProgressEvent);
    if (payload.privacy_present && payload.safe_text) {
      query.value = payload.safe_text;
      updateComposer();
    }
    showPayload(payload);
    rememberQuestion(payload);
  } catch (error) {
    failProgress("The request could not be completed");
    showResult(
      "error",
      "Service temporarily unavailable",
      "We could not process this request. Your question is still here, so you can retry.",
      "Request not completed",
    );
  } finally {
    thinkingPanel.hidden = true;
    isSubmitting = false;
    submit.disabled = false;
    clear.disabled = false;
    const label = submit.querySelector?.("span");
    if (label) label.textContent = "Get guidance";
    else submit.textContent = "Get guidance";
  }
});

renderHistory();
updateComposer();

fetch("/api/status", { cache: "no-store" })
  .then(response => { if (!response.ok) throw new Error(); return response.json(); })
  .then(body => {
    const statusText = status.querySelector?.("span:last-child") || status;
    if (!body.model_ready) {
      statusText.textContent = "Service unavailable";
      status.className = "service-status unavailable";
      setText("runtime-mode", "Classifier models unavailable");
      setText("runtime-detail", "Add the local model package to run the assistant");
      return;
    }
    statusText.textContent = "System ready";
    status.className = body.answer_generator_ready ? "service-status ready" : "service-status degraded";
    if (body.answer_generator_ready) {
      setText("runtime-mode", "Local NLU + Qwen");
      setText("runtime-detail", "Models initialized · no hosted answer API");
    } else if (body.answer_generator_status === "available_on_demand") {
      setText("runtime-mode", "Local NLU + Qwen on demand");
      setText("runtime-detail", "Answer model initializes on its first eligible response");
    } else {
      setText("runtime-mode", "Local NLU + verified fallback");
      setText("runtime-detail", "Answer model unavailable · verified guidance remains active");
    }
  })
  .catch(() => {
    const statusText = status.querySelector?.("span:last-child") || status;
    statusText.textContent = "Service unavailable";
    status.className = "service-status unavailable";
    setText("runtime-mode", "Backend unavailable");
    setText("runtime-detail", "Check that the local server is running");
  });

fetch("/api/guidance", { cache: "no-store" })
  .then(response => { if (!response.ok) throw new Error(); return response.json(); })
  .then(items => { catalog = items; if (!topicForm.hidden) updateTopicChoices(); })
  .catch(() => { catalogError = true; if (!topicForm.hidden) updateTopicChoices(); });
