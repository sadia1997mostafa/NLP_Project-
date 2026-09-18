const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function interfaceContext(fetchImpl) {
  const elements = new Map();
  function element() {
    return {
      hidden: false, textContent: "", value: "", children: [], listeners: {},
      addEventListener(name, handler) { this.listeners[name] = handler; },
      replaceChildren() { this.children = []; },
      appendChild(child) { this.children.push(child); },
    };
  }
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    createElement: element,
  };
  const context = vm.createContext({
    document, URL,
    fetch: fetchImpl || (async (url) => ({ json: async () => url === "/api/guidance" ? [] : { model_ready: true } })),
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../app/static/main.js"), "utf8"), context);
  return { context, elements };
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
    query_topic_id: selected.query_topic_id,
  }]);
  assert.equal(elements.get("result-title").textContent, selected.title);
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
