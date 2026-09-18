const form = document.getElementById("query-form");
const query = document.getElementById("query");
const submit = document.getElementById("submit-button");
const clear = document.getElementById("clear-button");
const count = document.getElementById("character-count");
const status = document.getElementById("service-status");
const result = document.getElementById("result");
const topicForm = document.getElementById("topic-form");
const topicService = document.getElementById("topic-service");
const topicChoice = document.getElementById("topic-choice");
const topicSubmit = document.getElementById("topic-submit");
let catalog = [];
let catalogError = false;

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
  result.hidden = false;
  result.className = `result ${state}`;
  setText("result-title", title);
  setText("result-body", body);
  setText("result-kicker", kicker);
  setVisible("scope-note", false);
  setVisible("privacy-notice", false);
  setVisible("result-source", false);
  setVisible("result-meta", false);
  topicForm.hidden = true;
  setVisible("result-documents", false);
  document.getElementById("document-list").replaceChildren();
}

function showPayload(payload) {
  const answer = payload.response;
  const labels = {
    answer: "Guidance",
    clarification: "Needs clarification",
    unavailable: "Guidance unavailable",
  };
  showResult(answer.state, answer.title, answer.body, labels[answer.state] || "Result");
  showTopics(payload.understanding?.service);
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
  if (payload.privacy_present) {
    setText("privacy-message", payload.warnings.join(" "));
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
}

topicService.addEventListener("change", updateTopicChoices);
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
        query_topic_id: item.query_topic_id,
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
  query.focus();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = query.value.trim();
  if (!text) return;
  submit.disabled = true;
  submit.textContent = "Working...";
  showResult("loading", "Checking your request", "", "In progress");
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
    submit.disabled = false;
    submit.textContent = "Get guidance";
  }
});

fetch("/api/status", { cache: "no-store" })
  .then((response) => response.json())
  .then((body) => {
    status.textContent = body.model_ready ? "Service available" : "Service unavailable";
    status.className = body.model_ready ? "service-status ready" : "service-status unavailable";
  })
  .catch(() => {
    status.textContent = "Service unavailable";
    status.className = "service-status unavailable";
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
