const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function interfaceContext(fetchImpl) {
  const elements = new Map();
  const stored = new Map();
  function element() {
    return {
      hidden: false, textContent: "", value: "", children: [], listeners: {},
      addEventListener(name, handler) { this.listeners[name] = handler; },
      focus() {},
      replaceChildren() { this.children = []; },
      appendChild(child) { this.children.push(child); },
    };
  }
  const document = {
    documentElement: { lang: "en" },
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    createElement: element,
  };
  const context = vm.createContext({
    document, URL,
    sessionStorage: {
      getItem(key) { return stored.has(key) ? stored.get(key) : null; },
      setItem(key, value) { stored.set(key, String(value)); },
      removeItem(key) { stored.delete(key); },
    },
    fetch: fetchImpl || (async (url) => ({ json: async () => url === "/api/guidance" ? [] : { model_ready: true } })),
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../app/static/main.js"), "utf8"), context);
  return { context, elements, stored };
}

function show(context, state, documents) {
  context.payload = {
    response: { state, title: "Test", body: "Guidance", required_documents: documents },
    privacy_present: false,
  };
  vm.runInContext("showPayload(payload)", context);
}

test("document conditions render as text, not HTML", () => {
  const { context, elements } = interfaceContext();
  show(context, "answer", ["Utility bill only if addresses differ", "<img src=x onerror=alert(1)>"]);
  assert.equal(elements.get("result-documents").hidden, false);
  assert.deepEqual(elements.get("document-list").children.map(item => item.textContent), [
    "Utility bill only if addresses differ", "<img src=x onerror=alert(1)>",
  ]);
});

test("a new answer replaces the previous checklist", () => {
  const { context, elements } = interfaceContext();
  show(context, "answer", ["Old document"]);
  show(context, "answer", ["New document"]);
  assert.equal(elements.get("document-list").children.length, 1);
  assert.equal(elements.get("document-list").children[0].textContent, "New document");
});

test("verified points render as text and clear on the next result", () => {
  const { context, elements } = interfaceContext();
  context.payload = {
    response: { state: "answer", match_level: "query_topic", title: "Test", body: "Answer",
      steps: ["Open the portal.", "<script>alert(1)</script>"] },
    understanding: { service: "PASSPORT" }, privacy_present: false,
  };
  vm.runInContext("showPayload(payload)", context);
  assert.equal(elements.get("result-steps").hidden, false);
  assert.equal(elements.get("step-list").children[1].textContent, "<script>alert(1)</script>");
  assert.equal(elements.get("topic-form").hidden, true);
  assert.equal(elements.get("change-topic").hidden, false);
  elements.get("change-topic").listeners.click();
  assert.equal(elements.get("topic-form").hidden, false);
  show(context, "clarification", []);
  assert.equal(elements.get("result-steps").hidden, true);
});

test("privacy notice survives a topic change but clears for a new query", () => {
  const { context, elements } = interfaceContext();
  context.payload = {
    response: { state: "clarification", title: "Clarify", body: "Choose a topic" },
    understanding: { service: "NID" }, privacy_present: true,
    warnings: ["Personal information was detected."],
  };
  vm.runInContext("showPayload(payload)", context);
  assert.equal(elements.get("privacy-notice").hidden, false);
  show(context, "answer", []);
  assert.equal(elements.get("privacy-notice").hidden, false);
  elements.get("clear-button").listeners.click();
  show(context, "answer", []);
  assert.equal(elements.get("privacy-notice").hidden, true);
});

test("privacy notice shows the protected question as masked tokens", () => {
  const { context, elements } = interfaceContext();
  context.payload = {
    response: { state: "answer", title: "NID update", body: "Follow the official steps." },
    understanding: { service: "NID" }, privacy_present: true,
    privacy_types: ["nid", "otp"], safe_text: "amar nid [NID], OTP [OTP]",
    warnings: ["Personal information was detected."],
  };
  vm.runInContext("showPayload(payload)", context);
  assert.equal(elements.get("masked-preview").hidden, false);
  const tokens = elements.get("masked-question").children.filter(item => item.className === "masked-token");
  assert.deepEqual(tokens.map(item => item.textContent), ["[NID]", "[OTP]"]);
});

test("recent questions store only server-protected text for the current tab", async () => {
  const { elements, stored } = interfaceContext(async (url) => {
    if (url === "/api/analyze") {
      return { ok: true, json: async () => ({
        response: { state: "answer", title: "NID update", body: "Use the official portal." },
        understanding: { service: "NID" }, privacy_present: true,
        privacy_types: ["nid"], safe_text: "amar nid [NID] update",
        warnings: ["Personal information was detected."],
      }) };
    }
    return { ok: true, json: async () => url === "/api/guidance" ? [] : { model_ready: true } };
  });
  elements.get("query").value = "amar nid 1234567890 update";
  await elements.get("query-form").listeners.submit({ preventDefault() {} });
  const serialized = stored.get("nagoriksheba.recentQuestions.v2");
  assert.match(serialized, /\[NID\]/);
  assert.doesNotMatch(serialized, /1234567890/);
  assert.equal(elements.get("history-list").hidden, false);
  assert.equal(elements.get("history-list").children.length, 1);
  elements.get("clear-history").listeners.click();
  assert.equal(stored.has("nagoriksheba.recentQuestions.v2"), false);
  assert.equal(elements.get("history-list").hidden, true);
});

test("Bengali answer labels preserve source-language transparency", () => {
  const { context, elements } = interfaceContext();
  context.payload = {
    response: { state: "answer", language: "bn", match_level: "query_topic",
      title: "Passport application", body: "নির্দেশনা", language_note: "উৎসের তথ্য ইংরেজিতে।" },
    understanding: { service: "PASSPORT" }, privacy_present: false,
  };
  vm.runInContext("showPayload(payload)", context);
  assert.equal(elements.get("result-kicker").textContent, "");
  assert.equal(elements.get("result-kicker").hidden, true);
  assert.equal(elements.get("language-note").hidden, false);
  assert.equal(elements.get("source-label").textContent, "সরকারি উৎস");
});

test("empty, clarification and unavailable responses clear the checklist", () => {
  const { context, elements } = interfaceContext();
  for (const [state, documents] of [["answer", []], ["clarification", ["ignored"]], ["unavailable", []]]) {
    show(context, "answer", ["Previous document"]);
    show(context, state, documents);
    assert.equal(elements.get("result-documents").hidden, true);
    assert.equal(elements.get("document-list").children.length, 0);
  }
});

test("loading and errors hide old documents and citations", () => {
  const { context, elements } = interfaceContext();
  for (const state of ["loading", "error"]) {
    show(context, "answer", ["Previous document"]);
    vm.runInContext(`showResult("${state}", "Test", "", "Test")`, context);
    assert.equal(elements.get("result-documents").hidden, true);
    assert.equal(elements.get("document-list").children.length, 0);
    assert.equal(elements.get("result-source").hidden, true);
  }
});

test("a guessed topic shows no answer until the visitor selects one", async () => {
  const selected = {
    service: "DRIVING_LICENCE", parent_topic_id: "DRIVING_LICENCE_LEARNER",
    query_topic_id: "DRIVING_LICENCE_LEARNER_DOCUMENTS", title: "Prepare learner licence documents",
  };
  const requests = [];
  const { context, elements } = interfaceContext(async (url, options) => {
    if (url === "/api/guidance" && options?.method === "POST") {
      requests.push(JSON.parse(options.body));
      return { ok: true, json: async () => ({
        response: { state: "answer", title: selected.title, body: "Bring relevant documents.",
          required_documents: ["Medical certificate"] },
        understanding: { service: selected.service }, privacy_present: false,
      }) };
    }
    return { ok: true, json: async () => url === "/api/guidance" ? [selected] : { model_ready: true } };
  });
  await new Promise(resolve => setImmediate(resolve));
  context.payload = {
    response: { state: "clarification", title: "Which topic did you mean?", body: "Select a topic." },
    understanding: { service: "DRIVING_LICENCE", query_topic_id: "DRIVING_LICENCE_LEARNER_ELIGIBILITY" },
    retrieval: { status: "found", match_level: "query_topic", record: null },
    privacy_present: false,
  };
  vm.runInContext("showPayload(payload)", context);
  assert.equal(elements.get("result-source").hidden, true);
  assert.equal(elements.get("topic-form").hidden, false);
  assert.equal(elements.get("topic-choice").value, "");
  assert.equal(elements.get("topic-submit").disabled, true);
  assert.equal(elements.get("topic-choice").children.length, 2);
  elements.get("topic-choice").value = "0";
  elements.get("topic-choice").listeners.change();
  await elements.get("topic-form").listeners.submit({ preventDefault() {} });
  assert.deepEqual(requests, [{
    service: selected.service, parent_topic_id: selected.parent_topic_id,
    query_topic_id: selected.query_topic_id, language: "en",
  }]);
  assert.equal(elements.get("result-title").textContent, "");
  assert.equal(elements.get("result-title").hidden, true);
  assert.equal(elements.get("result-body").textContent, "Bring relevant documents.");
  assert.equal(elements.get("document-list").children[0].textContent, "Medical certificate");
});

test("changing service clears the previous topic selection", () => {
  const { context, elements } = interfaceContext();
  vm.runInContext("catalog = [" + JSON.stringify({
    service: "DRIVING_LICENCE", parent_topic_id: "DRIVING_LICENCE_LEARNER",
    query_topic_id: "DRIVING_LICENCE_LEARNER_DOCUMENTS", title: "Learner documents",
  }) + "," + JSON.stringify({
    service: "PASSPORT", parent_topic_id: "PASSPORT_DOCUMENTS",
    query_topic_id: "PASSPORT_DOCUMENTS_REQUIRED", title: "Passport documents",
  }) + "]", context);
  vm.runInContext("showTopics('DRIVING_LICENCE')", context);
  elements.get("topic-choice").value = "0";
  elements.get("topic-choice").listeners.change();
  assert.equal(elements.get("topic-submit").disabled, false);
  elements.get("topic-service").value = "PASSPORT";
  elements.get("topic-service").listeners.change();
  assert.equal(elements.get("topic-choice").value, "");
  assert.equal(elements.get("topic-choice").children[1].textContent, "Passport documents");
  assert.equal(elements.get("topic-submit").disabled, true);
});

test("answer trace reports measured routing and grounding values", () => {
  const { context, elements } = interfaceContext();
  context.payload = {
    response: { state: "answer", language: "en", match_level: "query_topic",
      title: "Track a passport application", body: "Open Status Check.",
      answer_basis: "local_finetuned_model" },
    understanding: { service: "PASSPORT", service_routing: "lexical_anchor",
      overall_confidence: 0.873, topic_match_score: 0.624 },
    retrieval: { status: "found", match_level: "query_topic" },
    privacy_present: false,
  };
  vm.runInContext("showPayload(payload)", context);
  assert.equal(elements.get("pipeline-panel").hidden, false);
  assert.equal(elements.get("routing-confidence").textContent, "87%");
  assert.equal(elements.get("topic-confidence").textContent, "62%");
  assert.equal(elements.get("coverage-level").textContent, "Exact covered topic");
  assert.equal(elements.get("grounding-status").textContent, "Model + verified facts");
  assert.match(elements.get("trace-answer").textContent, /Local Qwen/);
});

test("processing panel is visible only while analysis is pending", async () => {
  let finish;
  const pending = new Promise(resolve => { finish = resolve; });
  const { elements } = interfaceContext(async (url) => {
    if (url === "/api/analyze") {
      await pending;
      return { ok: true, json: async () => ({
        response: { state: "clarification", title: "Clarify", body: "Choose a topic." },
        understanding: { service: "NID", overall_confidence: 0.5 },
        privacy_present: false,
      }) };
    }
    return { ok: true, json: async () => url === "/api/guidance" ? [] : { model_ready: true } };
  });
  elements.get("query").value = "NID correction";
  const request = elements.get("query-form").listeners.submit({ preventDefault() {} });
  assert.equal(elements.get("thinking-panel").hidden, false);
  assert.equal(elements.get("result").hidden, true);
  finish();
  await request;
  assert.equal(elements.get("thinking-panel").hidden, true);
  assert.equal(elements.get("result").hidden, false);
});
