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
let catalog = [];
let catalogError = false;
let lastPrivacyWarnings = [];
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

function setText(id, value) {
  document.getElementById(id).textContent = value || "";
}

function setVisible(id, visible) {
  document.getElementById(id).hidden = !visible;
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
  setText("result-title", title);
  setText("result-body", body);
  setText("result-kicker", kicker);
  setVisible("scope-note", false);
  setVisible("privacy-notice", false);
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
    ? `Masked: ${(payload.privacy_types || []).join(", ") || "personal information"}`
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
  };
  const basis = basisLabels[answer.answer_basis] || "No authoritative answer composed";
  setText("trace-answer", basis);
  setText("grounding-status", answer.answer_basis === "local_finetuned_model"
    ? "Model + verified facts" : answer.answer_basis === "curated_source_facts"
      ? "Verified fact plan" : "Routing only");

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
  if (answer.scope_note) {
    setText("scope-note", answer.scope_note);
    setVisible("scope-note", true);
  }
  if (payload.privacy_present) lastPrivacyWarnings = payload.warnings || [];
  if (lastPrivacyWarnings.length) {
    setText("privacy-message", lastPrivacyWarnings.join(" "));
    setVisible("privacy-notice", true);
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
  suggestedService = "";
  responseLanguage = "en";
  thinkingPanel.hidden = true;
  query.focus();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = query.value.trim();
  if (!text) return;
  submit.disabled = true;
  submit.textContent = "Working...";
  lastPrivacyWarnings = [];
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
  } catch (_) {
    showResult("error", "Service unavailable", "We could not process this request right now. Please try again later.", "System error");
  } finally {
    thinkingPanel.hidden = true;
    submit.disabled = false;
    submit.textContent = "Get guidance";
  }
});

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
