# bench: does the security plugin make Claude Code's code more secure?

This folder runs the pre-registered three-arm experiment on two benchmarks.
BaxBench comes first, as a 40-task pilot that proves the unattended gate
protocol and prices a task. SusVibes v1.0 follows in full, after the budget
is signed off.

| Arm | What runs | Container setup | First message |
| --- | --- | --- | --- |
| arm1 | Claude Code alone | `setup/common.sh` | the task prompt |
| arm2 | Claude Code with AI-DLC 2.11.3, scope `classic` | `common.sh`, `aidlc.sh` | `/aidlc --scope classic --project-type <type> <prompt>` |
| arm3 | arm2 with this repository's security plugin, strict mode | `common.sh`, `aidlc.sh`, `security.sh` | as arm2 |

`<type>` is `greenfield` on BaxBench, where the agent writes a new app, and
`brownfield` on SusVibes, where it changes an existing repository.

The arms differ only in these two columns. `arms.py` holds the table, and
`tests/test_bench.py` checks that the SusVibes commands of the three arms
differ only in the setup script, the driver wrapper that adds the first
message, and the run's own label and folder. Everything else comes from
`config.env` and is the same for every arm: the Claude Code version, the
Bedrock model and region, the driver, the timeout, the allowed and
disallowed tools, and how the patch or app is collected.

## Before you start

The experiment host needs:

- x86_64 Linux. The SusVibes task images exist for amd64 only.
- Docker that your user can run, and at least 500 GB of disk.
- Python 3.12 and git. Bun is not needed, because `build_assets.py`
  downloads the pinned bun and builds with it.
- Network access to GitHub, npm, PyPI and Docker Hub. Containers install
  Claude Code from npm and Node.js through nvm when the image has none.
- Bedrock access through the instance role. Containers use the host network,
  so Claude Code finds the role through the instance metadata service and no
  key goes into the environment. The model in `config.env` must be enabled in
  `AWS_REGION`.
- The SusVibes fork's branch `bench/aidlc-arms` pushed to
  `warren830/susvibes`. `bench.py setup` clones it from there.

Before arm3 runs, a person sets up AWS Security Agent once, by hand, as the
plugin's README describes: the `setup` that creates the IAM role
`SecurityAgentScanRole` and the agent space, then one threat model review and
one diff scan, so that both S3 buckets exist. The instance role needs the
Security Agent permissions in ap-southeast-1. No run may create AWS
resources, so every run disallows the MCP server's `setup` and its `call_api`,
which reaches every service operation, including billed pentests.

## Run the experiment

Make the driver's environment, then set up the work dir. Every command takes
`--work DIR`, default `./bench-work`, and `--config FILE`, default
`bench/config.env`.

```bash
python3.12 -m venv .venv-bench
.venv-bench/bin/pip install -r bench/requirements.txt
.venv-bench/bin/python bench/bench.py setup
```

`setup` clones the SusVibes fork at `SUSVIBES_FORK_COMMIT`, or at the head of
`SUSVIBES_FORK_BRANCH` when that is empty, and BaxBench at `BAXBENCH_REF`. It
makes a SusVibes virtualenv (`requirements.txt` and `pip install -e .`) and
BaxBench's pipenv environment, builds the assets, exports BaxBench's task
definitions, and records every commit in `bench-work/setup.json`.

The BaxBench pilot, one command per arm, one arm after another:

```bash
.venv-bench/bin/python bench/bench.py baxbench --arm arm1
.venv-bench/bin/python bench/bench.py baxbench --arm arm2
.venv-bench/bin/python bench/bench.py baxbench --arm arm3
.venv-bench/bin/python bench/bench.py report
```

Each arm runs the 40 tasks in `baxbench/pilot_tasks.json` with `WORKERS`
containers at a time (`--workers N` overrides it), then BaxBench's own
`--mode test` and `--mode evaluate` on exactly those tasks. A command run
again skips the tasks that already finished (`--force` runs them again).

SusVibes, after the budget sign-off, in the design's order:

```bash
for arm in arm1 arm2 arm3; do
  for run in 1 2 3; do
    .venv-bench/bin/python bench/bench.py susvibes --arm "$arm" --run "$run"
  done
done
.venv-bench/bin/python bench/bench.py report
```

Each call runs the fork's `parallel_batch_run.py` over
`datasets/default/susvibes_dataset.jsonl` with `--strategy none`, then
`python -m susvibes.eval.core` on the merged predictions.

`report` writes `bench-work/report/`: `rows.csv` (one row per benchmark,
task, arm and run), `summary.csv`, `budget.csv` and `report.md`. The budget
assumes that a SusVibes task costs and takes what a pilot task cost and took
in the same arm, over 186 tasks and 3 runs per arm. Next to it, the report
prices the run at the SusVibes leaderboard's Claude Code mean of $1.16 per
task (Claude Sonnet 4, v0.0).

### Run the driver on its own

The driver also runs `claude` on the host, in a directory, for a smoke test:

```bash
.venv-bench/bin/python bench/bench.py driver --local-cwd /tmp/smoke \
  --prompt-file prompt.txt --out-dir /tmp/smoke-out --timeout 1800 \
  --allowed-tools Bash,Edit,Write,Read,Glob,Grep,Skill,Task \
  --first-message-template '/aidlc --scope classic --project-type greenfield {prompt}'
```

`--claude-bin` picks the executable, default `claude`. The SDK bundles
Claude Code 2.1.318 at
`.venv-bench/lib/python3.12/site-packages/claude_agent_sdk/_bundled/claude`.
Here `claude` gets the driver's own environment, so export the Bedrock
variables from `config.env` first. To see AI-DLC's gates, run the arm's setup
parts in that directory first (`bench.py setup-script --arm arm2` prints
them). The local driver refuses to start when `AIDLC_UNATTENDED`,
`AIDLC_SKIP_HUMAN_PRESENCE_GUARD` or an `AIDLC_DISABLE_*` switch is set.

## Pins

`config.env` holds every pin, and each run copies it into its manifest.

| Pin | Value |
| --- | --- |
| `CLAUDE_CODE_VERSION` | 2.1.318, also the CLI the SDK in `requirements.txt` bundles |
| `ANTHROPIC_MODEL` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. **Open decision for warren.** |
| `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` | the same model. AI-DLC's reviewers pin `sonnet`, and Claude Code's Explore agent and small calls use `haiku`, so every alias points at the one model |
| `AWS_REGION` | us-east-1, the Bedrock region |
| `AIDLC_VERSION` | 2.11.3 |
| `PLUGIN_COMMIT` | `76ecd71`, the plugin under test |
| `AIDLC_WORKFLOWS_BUILD_COMMIT` | `cc22ef55`, the CI pin the plugin builds with (an ancestor of v2.11.3) |
| `SUSVIBES_FORK_COMMIT` | empty, so `setup` resolves the branch head and records it |
| `BAXBENCH_REF` | v1.0.0 |
| `TIMEOUT_SECONDS`, `WORKERS` | 10800, 8 |

## Where the results go

```text
bench-work/
├── setup.json                         commits, pins and the asset manifest
├── assets/                            what every container gets at /opt/bench-assets
├── runs/baxbench/results/<arm>/       BaxBench's layout: <scenario>/<env>/temp0.2-openapi-none/sample0/
│   ├── manifest.json                  pins, commits, host, start and end
│   └── setup-<arm>.sh                 the exact setup script that ran
├── runs/baxbench/artifacts/<arm>/<scenario>/<env>/
│                                      task.json, setup.log, driver.log and the driver's files
├── runs/susvibes/<arm>-run<k>/        the fork's results, predictions.json, manifest.json
└── report/
```

The driver writes `raw.jsonl` (the CLI's stdout as it wrote it),
`answers.jsonl` (one line per scripted answer), `permissions.jsonl` (tool
calls it denied) and `summary.json` (status, cost, tokens, turns, gate
counts and the AI-DLC state). BaxBench keeps the app from `/app/code`
without `node_modules`, `__pycache__`, `target`, `.venv` and `.git`
anywhere, and without `aidlc*`, `.aidlc*`, `.claude`, `CLAUDE.md`,
`AGENTS.md` and `.mcp.json` at its top.

## The gate protocol as implemented

The design's protocol (`experiment-design.md`, section 3) answers Approve at
an AI-DLC gate and "go with your recommendation" to a question, and never
overrides a blocking finding. The driver answers every `AskUserQuestion` from
one rule table in `driver/policy.py`. The first rule that matches answers,
and each answer is logged with its rule id.

| # | Rule id | The rule |
| --- | --- | --- |
| 1 | `override_offered_and_refused` | Never choose `Override blocking sensors` or `Accept the risk`. When either is offered, the answer records it as refused. |
| 2 | `fix_findings` | Choose `Fix findings` or `Fix it` when offered. |
| 3 | `approve` | Choose `Approve` when offered, or the plan approvals `Approve Plan`, `Approve Plans` and `Approve all`. |
| 4 | `recommended` | Choose the option whose label ends with `(Recommended)`; on a multi-select question, every such option. |
| 5 | `free_text` | Otherwise answer in free text: `Go with your recommendation.` |

Labels match without case and without the `(Recommended)` suffix, so
`Approve, but let's stop there for today` is not an approval.
`FREE_TEXT_REPLY` in `driver/policy.py` holds the free-text reply. It is the
design's fixed reply, 按你的推荐, in English to match the English prompts.

A turn that ends without a question is a prose turn. When the AI-DLC state
file shows a stage waiting at its gate (`[?]`), the driver sends `Approve`.
Otherwise it sends the free-text reply. Each run ends with one status:

| Status | When |
| --- | --- |
| `completed` | The state file says `Status: Completed` or `Next Action: Workflow complete`. In a project without AI-DLC, the first turn that ends. |
| `stuck` | 5 prose replies (`--stuck-after`) left the state file as it was, or the agent asks the same question a sixth time in a row. |
| `timeout` | `--timeout` passed. The driver interrupts the turn and waits up to 15 seconds for its result, then the SDK closes the CLI (end of input, then SIGTERM, then SIGKILL). |
| `error` | An error result, a CLI that exits, or a driver failure. |

Every other tool call that Claude Code puts to the driver is denied, as
`claude -p` denies it. `AskUserQuestion` is not in `ALLOWED_TOOLS`, so it
always reaches the driver.

## Decisions this code makes, with their evidence

Paths under `aidlc-workflows` are at tag v2.11.3. Paths under the SDK are in
`claude-agent-sdk` 0.2.178.

- **The task text rides in the first message, after the flags.** The skill
  passes its arguments to `aidlc engine orchestrate next` as they are
  (`harness/claude/skills/aidlc/SKILL.md:41` and `:48`), the engine reads the
  words after its flags as the request (`core/tools/aidlc-orchestrate.ts:6567`),
  stores them and creates the work from the stored copy
  (`core/tools/aidlc-orchestrate.ts:7070`), and the guide documents
  `/aidlc <description>` (`docs/guide/12-cli-commands.md:195`). With the real
  Claude Code 2.1.318, a multi-line prompt with quotes, backticks and `$`
  reaches the skill whole (`tests/test_driver_real_cli.py`). No second message
  is needed, so the driver has no `--then-send-prompt`.
- **Answers.** `updated_input` is the tool input plus `answers`, keyed by
  question text (`tests/harness/sdk-drive.ts:17-22`, `buildAnswers`). A
  multi-select answer is a list of labels. Claude Code 2.1.318's
  AskUserQuestion schema (in the bundled CLI binary) joins a list with `, `,
  and the real-CLI test sees both labels in the tool result.
- **When a turn is over.** A result frame ends a turn, not the session. As in
  `tests/harness/sdk-drive.ts:32-43` and `trackDriveTask` (`:437`), a task is
  pending from `task_started` until its `task_notification`, and a result
  whose pending tasks all finished (`task_updated`) waits 30 seconds
  (`SETTLED_TASK_REPORT_WAIT_MS`, `:420`) for a report. Only agent tasks count,
  as in the SDK (`_internal/query.py`, `DEFERRING_TASK_TYPES`). A background
  dev server never finishes, so tracking it would hold the turn until the
  timeout.
- **Cost is read, not summed.** In a streaming session Claude Code 2.1.318
  reports `total_cost_usd` and `modelUsage` as running totals ("read the
  latest result rather than summing across results", in the CLI's result
  schema), `usage` covers one turn's main loop only, and `num_turns` counts
  one turn. So `num_turns` is summed, cost and tokens come from the latest
  `modelUsage`, and a total that drops starts a new segment.
- **The workspace is not trusted.** Claude Code 2.1.318 ignores a project's
  `permissions.allow` until the workspace is trusted, and says so on stderr.
  No arm trusts it, so AI-DLC's own allow rules (`WebSearch` among them) do
  not apply and every arm has exactly `ALLOWED_TOOLS`. AI-DLC's hooks still
  run, as their heartbeats in the rehearsal below show.
- **AI-DLC install.** Offline from the release files
  (`docs/guide/18-install-and-lifecycle.md:214`, `--from`), `--allow-root` as
  root (`:220`), then `aidlc config --project-dir <dir> --harness claude
  --mcp none --quiet` (`:466`, `:1069`) and `aidlc doctor`. The project dir is
  `BENCH_PROJECT_DIR`, default `/project`; BaxBench passes `/app`. aidlc goes
  on the PATH in `/root/.claude_env`, which is sourced before `claude`, and a
  wrapper in `/usr/local/bin` puts it on the system PATH that doctor checks.
- **Plugin install.** `claude plugin marketplace add <assets>/security-plugin`
  and `claude plugin install security@security-aidlc-plugins` (user scope,
  both run without a prompt in 2.1.318), then `aidlc engine plugin sync` and
  `aidlc engine plugin select aidlc,security`
  (`docs/reference/18-plugin-mechanism.md`, sections 5 and 5a). The plugin's
  own SessionStart hook syncs again at each start.
- **MCP server.** Added at local scope (`security/README.md`, Configure the
  MCP server), so no project `.mcp.json` waits for an approval. The setup
  installs the pinned server with `uv tool install` and registers its
  executable, so its first start reads from disk instead of resolving with
  `uvx`. `AWS_REGION=ap-southeast-1` is set on the server; `AWS_PROFILE` only
  when set during setup.
- **Claude Code stays at its version.** `/root/.claude_env` sets
  `DISABLE_AUTOUPDATER=1` for every arm.
- **BaxBench agent image.** The env's own Dockerfile with BaxBench's RUN lines
  and no app. A COPY that names the app's file (Rust's `main.rs`) gets an
  empty one, and git and curl are added when the image lacks them.

## What was verified, and what still needs the experiment host

Verified offline on an arm64 host (no model call, no AWS call):

- The driver, with the real SDK, against a fake `claude` that speaks the
  stream-json control protocol, and through a fake `docker` that passes only
  the `-e` names into the "container" (`tests/test_driver_e2e.py`).
- The driver against the real Claude Code 2.1.318 that the SDK bundles, with
  a local fake Messages API in place of the model
  (`tests/test_driver_real_cli.py`).
- `build_assets.py` and `bench.py setup`, with the network.
- The arm3 setup bundle, as a non-root user with a scratch HOME: Claude Code
  2.1.318 from npm, AI-DLC 2.11.3 from the release files, `aidlc doctor`
  with 0 problems, the plugin composed and enabled (`plugin list` says
  `current`), the MCP server connected; a second run converged. With that
  install, the real CLI listed the plugin, the aidlc skill and the Security
  Agent tools without `setup` and `call_api`, and AI-DLC's hooks ran.

Mock only:

- The BaxBench runner's container steps, against a recording fake `docker`
  (`tests/test_baxbench.py`). The sampler and the task export ran on the real
  BaxBench v1.0.0 checkout.

Needs the experiment host:

- Any real container: root, `--allow-root`, nvm on images without Node 22,
  the `/usr/local/bin` wrapper, the BaxBench agent images and SusVibes images.
- Bedrock through the instance role, and AI-DLC and the plugin driven by a
  real model through whole workflows.
- BaxBench `--mode test` and `--mode evaluate` on the pilot's apps, and the
  SusVibes runner and evaluator.

One limit is known. Containers share the host's network, so agents that test
their app on port 5000 at the same time can reach each other's server.
BaxBench's own tests afterwards run in isolated containers. `--workers 1`
removes the overlap at the cost of time.
