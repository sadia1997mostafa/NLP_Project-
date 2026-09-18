const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function interfaceContext() {
  const elements = new Map();
  function element() {
    return {
      hidden: false, textContent: "", children: [],
      addEventListener() {},
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
    fetch: async () => ({ json: async () => ({ model_ready: true }) }),
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
