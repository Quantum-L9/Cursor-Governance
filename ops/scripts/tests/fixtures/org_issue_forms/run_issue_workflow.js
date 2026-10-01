// Run the `script: |` body of a vendored issue workflow against an issue body
// and print the label writes, comments and failures as JSON. Mirrors the
// runner's github-script bindings closely enough for the issue parsers;
// nothing here re-implements their rules.
//
//   node run_issue_workflow.js <workflow.yml> <body.md> [existing-labels-csv] [action]
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const [workflow, bodyFile, labelsCsv = "", action = "opened"] = process.argv.slice(2);
const lines = fs.readFileSync(workflow, "utf8").split("\n");
const start = lines.findIndex((l) => /^\s*script:\s*\|\s*$/.test(l));
if (start < 0) throw new Error(`no "script: |" block in ${workflow}`);
const indent = lines[start].match(/^\s*/)[0].length + 2;
const body = [];
for (const line of lines.slice(start + 1)) {
  if (line.trim() !== "" && line.match(/^\s*/)[0].length < indent) break;
  body.push(line.slice(indent));
}

const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "org-issue-form-"));
const mod = path.join(scratch, "script.js");
fs.writeFileSync(
  mod,
  `module.exports = async (github, core, context, require) => {\n${body.join("\n")}\n};\n`,
);

const added = [];
const removed = [];
const comments = [];
const failures = [];
const warnings = [];
const github = {
  rest: {
    issues: {
      addLabels: async (a) => added.push(...a.labels),
      removeLabel: async (a) => removed.push(a.name),
      createComment: async (a) => comments.push(a.body),
    },
  },
};
const core = {
  setFailed: (m) => failures.push(m),
  warning: (m) => warnings.push(m),
  info() {},
  notice() {},
};
const context = {
  repo: { owner: "o", repo: "r" },
  payload: {
    action,
    issue: {
      number: 1,
      body: fs.readFileSync(bodyFile, "utf8"),
      labels: labelsCsv
        .split(",")
        .filter(Boolean)
        .map((name) => ({ name })),
    },
  },
};

const sort = (a) => [...a].sort((x, y) => x.localeCompare(y));
require(mod)(github, core, context, require)
  .then(() => {
    process.stdout.write(
      JSON.stringify({
        added: sort(added),
        removed: sort(removed),
        comments,
        failures,
        warnings,
      }),
    );
  })
  .finally(() => fs.rmSync(scratch, { recursive: true, force: true }));
