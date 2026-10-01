// Run the `script: |` body of a vendored github-script workflow against a PR
// body and print the failures as JSON. Mirrors the runner's bindings closely
// enough for the PR-body validators; nothing here re-implements their rules.
//
//   node run_workflow_script.js <workflow.yml> <body.md> [name-status.txt]
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const [workflow, bodyFile, nameStatus] = process.argv.slice(2);
const lines = fs.readFileSync(workflow, "utf8").split("\n");
const start = lines.findIndex((l) => /^\s*script:\s*\|\s*$/.test(l));
if (start < 0) throw new Error(`no "script: |" block in ${workflow}`);
const indent = lines[start].match(/^\s*/)[0].length + 2;
const body = [];
for (const line of lines.slice(start + 1)) {
  if (line.trim() !== "" && line.match(/^\s*/)[0].length < indent) break;
  body.push(line.slice(indent));
}

const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "org-pr-gate-"));
let script = body.join("\n").replace(/\$\{\{\s*inputs\.strict\s*\}\}/g, "true");
// pr-files reads the diff its preceding run: step wrote to the runner's
// scratch dir; serve it from a private temp dir instead.
script = script.replace(
  /(["'])\/tmp\/(changed|shortstat)\.txt\1/g,
  (_m, q, n) => q + path.join(scratch, `${n}.txt`) + q,
);
fs.writeFileSync(
  path.join(scratch, "changed.txt"),
  nameStatus ? fs.readFileSync(nameStatus, "utf8") : "",
);
fs.writeFileSync(path.join(scratch, "shortstat.txt"), "");
const mod = path.join(scratch, "script.js");
fs.writeFileSync(
  mod,
  `module.exports = async (github, core, context, require) => {\n${script}\n};\n`,
);

const failures = [];
const findings = [];
const summary = {
  addHeading: () => summary,
  addList: (items) => {
    findings.push(...items);
    return summary;
  },
  addRaw: () => summary,
  write: async () => summary,
};
const core = { setFailed: (m) => failures.push(m), notice() {}, info() {}, summary };
let updatedBody = null;
const github = {
  rest: {
    pulls: {
      update: async ({ body: next }) => {
        updatedBody = next;
      },
    },
  },
};
const context = {
  payload: {
    pull_request: {
      body: fs.readFileSync(bodyFile, "utf8"),
      number: 1,
      draft: false,
      user: { login: "l9" },
    },
  },
  repo: { owner: "o", repo: "r" },
};

require(mod)(github, core, context, require)
  .then(() => {
    process.stdout.write(JSON.stringify({ failures, findings, updatedBody }));
  })
  .finally(() => fs.rmSync(scratch, { recursive: true, force: true }));
