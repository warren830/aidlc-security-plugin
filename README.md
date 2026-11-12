# aidlc-security-plugin

AWS Security Agent for [AI-DLC](https://github.com/awslabs/aidlc-workflows).

- [`security/`](security/README.md) is the AI-DLC plugin `security`: a threat
  model of the approved design in Inception, and a diff scan with a blocking
  findings gate on Code Generation. Its README covers installation, the MCP
  server setup, what runs in your AWS account, and the gate's rules.
- [`replay/`](replay/README.md) is a validation suite: minimal scenarios, where
  each should be detected, and what the current implementation detects.
  `bun run replay` writes its [`REPORT.md`](replay/REPORT.md), and CI runs
  `bun run replay:check`. The report scores each case twice, with the plugin
  on and with AI-DLC core alone, which is the plugin off.
- [`bench/`](bench/README.md) runs Claude Code alone, with AI-DLC, and with
  AI-DLC and this plugin, on BaxBench and SusVibes. The
  [BaxBench pilot results](bench/results/baxbench-pilot-2026-11-08/README.md)
  compare the plugin off and on, task by task.
- [`aidlc-security-action`](https://github.com/warren830/aidlc-security-action)
  is the GitHub Action, in its own repository. It runs this plugin's
  `security-findings-gate` worker, pinned to a plugin commit, on the same
  `security-scan-result.md`, so CI and the local gate reach the same verdict.

## Development

The plugin authoring tools (`aidlc-plugin-validate`, `-build`, `-test`) and
the `plugin-kit` test helpers ship in an aidlc-workflows checkout, not as a
package. Build one, then point `AIDLC_WORKFLOWS_DIR` at it. The default is
`../aidlc-workflows`, beside this repository.

```bash
git clone https://github.com/awslabs/aidlc-workflows ../aidlc-workflows
git -C ../aidlc-workflows checkout cc22ef5564b159553057962ea874d4e1b855ccad
(cd ../aidlc-workflows && bun install --frozen-lockfile && bun scripts/package.ts)
bun install
```

CI pins that commit. A newer aidlc-workflows can change what the tools
accept, so move the pin in `.github/workflows/ci.yml` and here together.

| Command | What it runs |
| --- | --- |
| `bun run validate` | `aidlc-plugin-validate` on `security/` |
| `bun run build:claude`, `bun run build:kiro-ide` | `aidlc-plugin-build`, into `security/dist/<harness>/` |
| `bun run typecheck` | `tsc` over `scripts/`, the plugin's tools and `tests/` |
| `bun run lint` | `biome check --error-on-warnings` |
| `bun run test` | The tests in `tests/`, listed below |

`bun run test` checks, for the Claude Code and Kiro IDE projections:

- the shipped validator accepts the plugin;
- the threat model stage's Step 6 lists the sections of the plugin's
  threat model template, in the same order;
- each projection composes into a scratch install with no drops, with the
  threat model stage in Inception, the gate check on Code Generation, and the
  baseline and persona fragments on the DevSecOps agent;
- the shipped `aidlc-plugin-test` passes against a scratch install;
- the composed install's own dispatcher fires the gate check on an accepted
  finding, and the check blocks it without `.aidlc-security.json` and passes
  it with a lenient one;
- the same dispatcher fires the check on a unit whose threat model has a HIGH
  threat with no evidence, and the check passes it in warn mode and blocks it
  in block mode;
- the same dispatcher fires core's `required-sections` on the threat model,
  against the template that compose put in the install: a complete threat
  model passes, and one without `## Repudiation` fails, and the detail file
  names that section;
- the gate check's verdict for every committed record in
  `tests/fixtures/scan-records/` and in the record trees under
  `tests/fixtures/records/`, through the worker as a subprocess and through
  `main(argv)`, in the override and coverage modes that the project folders in
  `tests/fixtures/projects/` set.

The tests make no AWS call: the gate check reads only files, and nothing
starts the MCP server.

`scripts/plugin-tool.ts` runs any of the authoring tools directly, for
example `bun scripts/plugin-tool.ts test security --install <project> --harness claude`.
