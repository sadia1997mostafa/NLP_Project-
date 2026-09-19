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
const historyKey = "nagoriksheba.recentQuestions.v2";
const legacyHistoryKeys = ["nagoriksheba.recentQuestions.v1"];
const historyLimit = 8;
let catalog = [];
let catalogError = false;
let lastPrivacyWarnings = [];
let lastMaskedQuestion = "";
let suggestedService = "";
let responseLanguage = "en";

const serviceNames = {
  NID: "National ID",
  BIRTH_REGISTRATION: "Birth registration",
  PASSPORT: "Passport",
  TAX: "Tax",
  POLICE_GD: "Police general diary",
  DRIVING_LICENCE: "Driving licence",
};

const privacyNames = {
  birth_registration: "birth registration",
  driving_licence: "driving licence",
  application_id: "application/reference ID",
  date_of_birth: "date of birth",
};

function setText(id, value) {
  document.getElementById(id).textContent = value || "";
}

function setVisible(id, visible) {
  document.getElementById(id).hidden = !visible;
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
      count.textContent = `${query.value.length} / 4000`;
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

function showTopics(suggestedService = "") {
  topicForm.hidden = false;
  topicService.replaceChildren();
  addOption(topicService, "Select a service", "");
  for (const [service, name] of Object.entries(serviceNames)) {
    addOption(topicService, name, service);
  }
  topicService.value = serviceNames[suggestedService] ? suggestedService : "";
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
  result.hidden = false;
  result.className = `result ${state}`;

  const conversationalAnswer = state === "answer";

  setText("result-title", conversationalAnswer ? "" : title);
  setVisible("result-title", !conversationalAnswer && Boolean(title));

  setText("result-body", body);

  setText("result-kicker", conversationalAnswer ? "" : kicker);
  setVisible("result-kicker", !conversationalAnswer && Boolean(kicker));

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

function percent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "Not scored";
  return `${Math.round(Math.max(0, Math.min(1, number)) * 100)}%`;
}

function showPipeline(payload) {
  const understanding = payload.understanding;
  const answer = payload.response;
  if (!understanding || !answer) return;

  const privacyDetail = payload.privacy_present
    ? `Masked: ${(payload.privacy_types || []).map(type => privacyNames[type] || type).join(", ") || "personal information"}`
    : "No personal identifiers detected";
  setText("trace-privacy", privacyDetail);

  const service = serviceNames[understanding.service] || understanding.service || "Unconfirmed";
  const routingMethod = understanding.service_routing === "lexical_anchor"
    ? "explicit service wording"
    : understanding.service_routing === "user_selected"
      ? "selected by user"
      : understanding.service_resolution === "explicit_name_correction"
        ? "corrected by explicit wording"
        : "local classifier";
  setText("trace-service", `${service} · ${routingMethod}`);

  const matchLabels = {
    query_topic: "Exact covered topic",
    parent_topic: "General topic guidance",
    service: "Service overview",
  };
  const matchLevel = answer.match_level || payload.retrieval?.match_level;
  const topicLabel = matchLabels[matchLevel] || "Topic not confirmed";
  const topicScore = understanding.topic_match_score ?? understanding.parent_match_score;
  setText("trace-topic", topicScore == null ? topicLabel : `${topicLabel} · ${percent(topicScore)} corpus match`);

  const basisLabels = {
  local_finetuned_model: "Local Qwen wording, checked against verified facts",
  curated_source_facts: "Controlled wording from verified facts",
  exact_intent_answer_plan: "Controlled wording from an exact verified answer plan",
};
  const basis = basisLabels[answer.answer_basis] || "No authoritative answer composed";
  setText("trace-answer", basis);
  setText(
  "grounding-status",
  answer.answer_basis === "local_finetuned_model"
    ? "Model + verified facts"
    : answer.answer_basis === "curated_source_facts"
      ? "Verified fact plan"
      : answer.answer_basis === "exact_intent_answer_plan"
        ? "Verified answer plan"
        : "Routing only"
);

  const routingConfidence = understanding.overall_confidence ?? understanding.service_confidence;
  setText("routing-confidence", percent(routingConfidence));
  setText("topic-confidence", percent(topicScore));
  setText("coverage-level", matchLabels[matchLevel] || "Unconfirmed");
  setVisible("pipeline-panel", true);
}

function showPayload(payload) {
  const answer = payload.response;
  responseLanguage = answer.language || responseLanguage;
  const bengali = responseLanguage === "bn";
  const labels = {
    answer: bengali ? "নির্দেশনা" : "Guidance",
    clarification: bengali ? "আরও তথ্য প্রয়োজন" : "Needs clarification",
    unavailable: bengali ? "নির্দেশনা নেই" : "Guidance unavailable",
  };
  showResult(answer.state, answer.title, answer.body, labels[answer.state] || "Result");
  document.documentElement.lang = responseLanguage;
  setText("steps-heading", bengali ? "যাচাইকৃত তথ্য" : "Verified guidance");
  setText("documents-heading", bengali ? "প্রয়োজনীয় নথি ও তথ্য" : "Documents and details");
  setText("source-label", bengali ? "সরকারি উৎস" : "Official source");
  if (answer.language_note) {
    setText("language-note", answer.language_note);
    setVisible("language-note", true);
  }
  suggestedService = payload.understanding?.service || suggestedService;
  if (answer.state !== "answer" || answer.match_level !== "query_topic") {
    showTopics(suggestedService);
  } else {
    changeTopic.hidden = false;
  }
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
    if (url.protocol === "https:" && url.hostname.endsWith(".gov.bd")) {
      link.href = url.href;
      link.textContent = answer.source.name;
      setText("source-date", `Reviewed ${answer.source.last_verified}`);
      setVisible("result-source", true);
    }
  }
  if (payload.understanding && answer.state === "answer") {
    const understanding = payload.understanding;
    setText("service-name", serviceNames[understanding.service] || understanding.service);
    setText("topic-name", answer.title);
    setText("priority-name", understanding.priority ? `Priority: ${understanding.priority}` : "");
    setVisible("result-meta", true);
  }
  showPipeline(payload);
}

topicService.addEventListener("change", updateTopicChoices);
changeTopic.addEventListener("click", () => {
  showTopics(suggestedService);
  changeTopic.hidden = true;
});
topicChoice.addEventListener("change", () => {
  topicSubmit.disabled = !topicChoice.value;
});

topicForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const item = catalog[Number(topicChoice.value)];
  if (!item || item.service !== topicService.value) return;
  topicSubmit.disabled = true;
  setVisible("topic-error", false);
  try {
    const response = await fetch("/api/guidance", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        service: item.service, parent_topic_id: item.parent_topic_id,
        query_topic_id: item.query_topic_id, language: responseLanguage,
      }), cache: "no-store",
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

query.addEventListener("input", () => {
  count.textContent = `${query.value.length} / 4000`;
});

clear.addEventListener("click", () => {
  query.value = "";
  count.textContent = "0 / 4000";
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
  try {
    sessionStorage.removeItem(historyKey);
  } catch (_) {
    // Storage may be unavailable in a restricted browser context.
  }
  renderHistory();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = query.value.trim();
  if (!text) return;
  submit.disabled = true;
  submit.textContent = "Working...";
  lastPrivacyWarnings = [];
  lastMaskedQuestion = "";
  suggestedService = "";
  responseLanguage = "en";
  result.hidden = true;
  thinkingPanel.hidden = false;
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error("Service unavailable");
    }
    const payload = await response.json();
    if (payload.privacy_present && payload.safe_text) {
      query.value = payload.safe_text;
      count.textContent = `${query.value.length} / 4000`;
    }
    showPayload(payload);
    rememberQuestion(payload);
  } catch (_) {
    showResult("error", "Service unavailable", "We could not process this request right now. Please try again later.", "System error");
  } finally {
    thinkingPanel.hidden = true;
    submit.disabled = false;
    submit.textContent = "Get guidance";
  }
});

renderHistory();

fetch("/api/status", { cache: "no-store" })
  .then((response) => response.json())
  .then((body) => {
    status.textContent = body.model_ready ? "System ready" : "Service unavailable";
    status.className = body.model_ready ? "service-status ready" : "service-status unavailable";
    setText("runtime-mode", body.answer_generator_ready
      ? "Classifier + local Qwen"
      : body.model_ready ? "Classifier + verified fallback" : "Models unavailable");
  })
  .catch(() => {
    status.textContent = "Service unavailable";
    status.className = "service-status unavailable";
    setText("runtime-mode", "Models unavailable");
  });

fetch("/api/guidance", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error("Topics unavailable");
    return response.json();
  })
  .then((items) => {
    catalog = items;
    if (!topicForm.hidden) updateTopicChoices();
  })
  .catch(() => {
    catalogError = true;
    if (!topicForm.hidden) updateTopicChoices();
  });
