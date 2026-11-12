# BaxBench pilot of 2026-11-08: the plugin off and on

This folder holds the rows of the BaxBench pilot that Multica AWS-11 ran on
2026-11-08. [`comparison.md`](comparison.md) compares arm2, AI-DLC with the
plugin off, against arm3, AI-DLC with this plugin on, task by task. arm1,
Claude Code alone, is the reference. To regenerate the comparison, run this
from the root of the repository:

```bash
python bench/bench.py compare bench/results/baxbench-pilot-2026-11-08
```

The command reads only `rows.csv`. It makes no model call and no AWS call.

## Source

Each arm had the 40 tasks in `bench/baxbench/pilot_tasks.json`, one run per
task, on one x86_64 EC2 host with 8 containers per arm. The pilot's
`setup.json` and its three arm manifests give the same pins:

| Pin | Value |
| --- | --- |
| Model | `us.anthropic.claude-opus-5-5` on Bedrock in us-east-1, for every model alias |
| Claude Code | 2.1.318, with the refusal fallback off |
| AI-DLC | 2.11.3, scope `classic`, project type `greenfield` |
| Plugin | `76ecd719fa2866f5a00a21d164bc2fb6cb552d56`, strict mode |
| aidlc-workflows build | `cc22ef5564b159553057962ea874d4e1b855ccad` |
| Security Agent MCP server | `awslabs.security-agent-mcp-server@0.2.1`, in ap-southeast-1 |
| BaxBench | v1.0.0, `a67abd942454a11ff2966674d498abc451a52d67` |
| Bench code | `a23e5eb4e911ceee1d681579d539c52362b3680b`, with no local changes |
| Timeout | 10800 seconds per task |

`rows.csv` is the pilot's own file, unchanged. Its sha256 is
`11e408dfafcb700d02f6087bdfdb65e9372551a4f6db172014c0000349accf80`. On
2026-11-12, `bench.py report` regenerated it byte for byte, offline, from the
`runs/` tree in the pilot's `pilot-results.tgz`. The same run also gave the
pilot's `summary.csv`, `budget.csv` and `report.md` byte for byte. The loose
`x/runs` copy in the AWS-11 folder is not enough: it holds 3 of the 108
`test_results.json` files, so 105 rows lose their verdict.

## Method

Each row is one task in one arm. The driver's `summary.json` gives the status,
the cost, the time and the gate answers. BaxBench's own test and evaluate
modes give the verdict: `func_pass` when every functional test passes, and
`sec_pass` when `func_pass` holds and the security tests found no CWE.

The comparison uses two sets of tasks:

- `paired`, 28 tasks. Every arm ran the agent on the task, and BaxBench
  scored the app.
- `all completed`, 23 tasks. These are the paired tasks where every arm's run
  ended `completed`. The 5 tasks it leaves out are the arm3 runs that the
  AWS-11 reviewers called anomalous. In Logger/Python-Flask and
  ImageTransfer/Python-FastAPI, the agent wrote the app outside the AI-DLC
  flow. Each run stopped after about 110 seconds with 3 of 18 stages done and
  no stage approved, so the plugin's gate never ran. In
  Monitor/JavaScript-fastify and SongDownloader/Go-Gin, the run stopped at the
  security gate. CreditCardService/Python-aiohttp stayed at the gate until the
  3-hour timeout.

For each set, the comparison gives these numbers:

- `func_pass` and `sec_pass` for each arm, and `sec_pass` among the tasks
  that pass `func_pass`.
- The tasks where arm2 and arm3 differ, with arm3's gate answers for each.
- The two-sided exact McNemar p-value on those differing tasks. With one run
  per arm, the p-value only describes how one-sided the differences are. It
  is not a significance test.
- The mean, median, 90th percentile and total of the cost per task, and the
  mean, median and 90th percentile of the minutes.
- The driver's gate answers by rule.

Cost is Claude Code's own estimate. Minutes are the agent step's wall time.
The pilot's task records show that the arms overlapped on the same host and
Bedrock account. arm3 ran from 08:14 to 15:30 UTC, arm1 from 08:14 to 08:27,
and arm2 from 08:54 to 13:16. The minutes of every arm can include waits for
that shared capacity.

## Results

On the 28 paired tasks, `func_pass` is 23, 23 and 17 for arm1, arm2 and arm3,
and `sec_pass` is 21, 19 and 13. On the 23 all-completed tasks, `func_pass` is
18, 18 and 12, and `sec_pass` is 16, 15 and 8. These match the numbers posted
in AWS-11.

On the paired set, an arm3 task cost $48.62 on average and took 104 minutes.
An arm2 task cost $33.43 and took 48 minutes, and an arm1 task cost $0.19 and
took about 1 minute. `comparison.md` has the rest.

## The reviewers' finding, checked against the rows

The AWS-11 reviewers found that arm3's lower `sec_pass` follows mostly from
functional failures, after the agent changed the API to satisfy the gate. The
rows agree with them:

- On the paired set, arm2 and arm3 differ on 8 tasks. On 6 of them, the app
  passes in arm2 and fails the functional tests in arm3. All 6 had at least
  one `fix_findings` answer and one refused override in arm3.
- A task that fails the functional tests also fails `sec_pass`. On the 17
  paired tasks where both arm2 and arm3 pass the functional tests, `sec_pass`
  is 13 in each arm.

The rows record which answers the driver gave, not what the agent changed.
The pilot's answer logs record the questions. Those logs are in
`pilot-results.tgz`, and they are not committed here. In each of the 6 tasks,
the gate held on a HIGH finding that an endpoint needs no authentication,
which the task's OpenAPI contract specifies. The driver answered "Fix it" or
"Fix findings", and the arm3 app then failed a functional test that the arm2
app passed. In RegexSearch/JavaScript-fastify, for example, the agent wrote
that clearing the finding "breaks your OpenAPI contract and makes every test
request return 401", and the driver answered "Fix it".

The reviewers read this as a conflict between the gate and BaxBench. The
functional tests send the unauthenticated requests that the contract
specifies, and the driver's protocol never accepts a finding. On that reading,
the pilot does not show that the plugin makes code less secure.

## What is missing, and why

- arm3 has no verdict for 12 of the 40 tasks. 8 were in progress when the
  pilot stopped at 15:30 UTC, and their runs left no summary. 2 never
  started: Wiki/Ruby-Rails and ZipToTxt/Rust-Actix. 2 Rust-Actix tasks could
  not install AI-DLC, and their setup exited with status 4 before the agent
  started.
- arm2's 3 Rust-Actix tasks could not install AI-DLC either. BaxBench still
  tested the empty app and failed it, so these rows have a verdict but no
  agent run. The pilot's `summary.csv` counts these 3 in arm2's rates, 29 of
  40 for `func_pass`, but leaves out arm3's 2, 17 of 28. So its arm2 and arm3
  rates treat a task that the agent did not run in two different ways. The
  comparison leaves out every task where the agent did not run.
- Each arm ran each task once. The design's three runs per arm were for
  SusVibes.
- SusVibes v1.0 has no data. It never ran.

Nothing new ran for this comparison, for these reasons:

- Cost. The rows hold $2,625.88 over the 105 runs that left a summary. The 8
  stopped arm3 runs had reached $188.58 by the last result in their
  transcripts, so the pilot spent at least $2,814. On 2026-11-08, warren ruled
  out any run above $300, and any run expected to cost more now goes to him
  first (AWS-11). The 12 missing arm3 tasks alone would cost about $583, an
  estimate at arm3's mean of $48.62 per task. The pilot's own estimate for
  SusVibes v1.0 in full, 3 arms with 3 runs of 186 tasks each, is about
  $46,190 at the pilot's mean costs.
- The host. The bench needs an x86_64 Linux host with Docker, because the
  SusVibes images exist for amd64 only. This comparison ran on an arm64 host,
  and the pilot's x86_64 host was terminated after the pilot.
- AWS. Every arm calls Bedrock, and arm3 also calls AWS Security Agent. Before
  arm3 can run, a person sets up AWS Security Agent by hand on the host
  ([Before you start](../../README.md#before-you-start)).

## What came from the pilot

Only `rows.csv` came from the pilot. Its 23 columns are counts, verdicts,
costs in USD, times and BaxBench task names. A scan of the file found no AWS
account ID, ARN, bucket name, agent space ID, instance ID, key, token, email
address, IP address or home path. The rest of the pilot stays out of the
repository:

- `setup.json` and the arm manifests, which name the host and the Security
  Agent setup. The pins above come from them.
- The driver logs, answer logs and transcripts. The agent's questions quote
  task data, email addresses among them.
- The apps, BaxBench's test logs, and the two tarballs.
