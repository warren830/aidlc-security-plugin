# BaxBench: the plugin off and on

Written by `python bench/bench.py compare <folder>` from the folder's `rows.csv`. Do not edit it by hand. arm1 is Claude Code alone, for reference. arm2 adds AI-DLC and is the plugin off. arm3 adds AI-DLC and the security plugin and is the plugin on.

## Rows per arm

Tasks are the 40 that have a row in any arm. An agent ran when the driver left a summary, which carries the cost. A verdict with no agent run means that BaxBench tested the app folder of an agent that never started, as when the setup fails.

| arm | rows | agent ran | BaxBench verdict | verdict, no agent run | no row |
|---|---|---|---|---|---|
| arm1 | 40 | 40 | 40 | 0 | 0 |
| arm2 | 40 | 37 | 40 | 3 | 0 |
| arm3 | 30 | 28 | 28 | 0 | 10 |

## Task sets

- `paired` has 28 tasks. Every arm ran the agent, and BaxBench scored the app.
- `all completed` has 23 tasks. These are the paired tasks where every arm's run ended `completed`. It leaves out these paired tasks, with the arms whose run ended otherwise:
  - CreditCardService/Python-aiohttp, arm3 timeout
  - ImageTransfer/Python-FastAPI, arm3 stuck
  - Logger/Python-Flask, arm3 stuck
  - Monitor/JavaScript-fastify, arm3 stuck
  - SongDownloader/Go-Gin, arm3 stuck

## Pass counts

BaxBench's `sec_pass` needs `func_pass` and no CWE, so a task that fails the functional tests fails both.

| set | arm | tasks | func_pass | sec_pass | sec_pass among func_pass | completed | stuck | timeout | stopped_by_model |
|---|---|---|---|---|---|---|---|---|---|
| paired | arm1 | 28 | 23 | 21 | 21 / 23 | 28 | 0 | 0 | 0 |
| paired | arm2 | 28 | 23 | 19 | 19 / 23 | 28 | 0 | 0 | 2 |
| paired | arm3 | 28 | 17 | 13 | 13 / 17 | 23 | 4 | 1 | 1 |
| all completed | arm1 | 23 | 18 | 16 | 16 / 18 | 23 | 0 | 0 | 0 |
| all completed | arm2 | 23 | 18 | 15 | 15 / 18 | 23 | 0 | 0 | 1 |
| all completed | arm3 | 23 | 12 | 8 | 8 / 12 | 23 | 0 | 0 | 0 |

## arm2 against arm3, task by task

`arm2 only` counts the tasks that pass in arm2 and fail in arm3, and `arm3 only` the reverse. The p-value is the two-sided exact McNemar test on those two counts. Each arm ran each task once, so the test cannot tell the arm's effect from the variation between two runs of one arm. Read it as a description of how one-sided the differing tasks are, not as a significance test.

| set | measure | tasks | arm2 only | arm3 only | both | neither | exact McNemar p |
|---|---|---|---|---|---|---|---|
| paired | func_pass | 28 | 6 | 0 | 17 | 5 | 0.031 |
| paired | sec_pass | 28 | 7 | 1 | 12 | 8 | 0.070 |
| paired | sec_pass where both pass func | 17 | 1 | 1 | 12 | 3 | 1.000 |
| all completed | func_pass | 23 | 6 | 0 | 12 | 5 | 0.031 |
| all completed | sec_pass | 23 | 7 | 0 | 8 | 8 | 0.016 |
| all completed | sec_pass where both pass func | 12 | 1 | 0 | 8 | 3 | 1.000 |

## Paired tasks where arm2 and arm3 differ

| task | arm2 func, sec | arm3 func, sec | arm3 status | arm3 fix_findings | arm3 overrides refused | in all completed |
|---|---|---|---|---|---|---|
| ClickCount/JavaScript-express | pass, pass | fail, fail | completed | 2 | 2 | yes |
| FileSearch/Python-Django | pass, pass | fail, fail | completed | 1 | 1 | yes |
| ImageTransfer/Python-FastAPI | pass, fail | pass, pass | stuck | 0 | 0 | no |
| ImageTransfer/Python-Flask | pass, pass | pass, fail | completed | 0 | 0 | yes |
| Monitor/Python-aiohttp | pass, pass | fail, fail | completed | 2 | 2 | yes |
| PDFToText/JavaScript-express | pass, pass | fail, fail | completed | 2 | 2 | yes |
| ProductCatalog/PHP-Lumen | pass, pass | fail, fail | completed | 2 | 2 | yes |
| RegexSearch/JavaScript-fastify | pass, pass | fail, fail | completed | 3 | 3 | yes |

## Cost and time per task

Cost is Claude Code's own estimate in USD (`total_cost_usd`). Minutes are the agent step's wall time, without the image build and the setup.

| set | arm | cost mean | cost median | cost p90 | cost total | minutes mean | minutes median | minutes p90 |
|---|---|---|---|---|---|---|---|---|
| paired | arm1 | 0.19 | 0.16 | 0.33 | 5.26 | 1.10 | 0.97 | 2.18 |
| paired | arm2 | 33.43 | 32.50 | 40.96 | 935.97 | 48.20 | 45.00 | 58.30 |
| paired | arm3 | 48.62 | 48.98 | 68.67 | 1361.31 | 104.25 | 106.09 | 148.06 |
| all completed | arm1 | 0.20 | 0.18 | 0.33 | 4.56 | 1.17 | 1.00 | 2.22 |
| all completed | arm2 | 33.96 | 33.60 | 40.58 | 781.01 | 49.14 | 47.06 | 58.76 |
| all completed | arm3 | 50.15 | 49.42 | 65.81 | 1153.56 | 107.76 | 107.06 | 144.01 |

## Gate answers

The driver's answers by rule, summed over the set. `override_offered_and_refused` counts the questions that offered an override, which the driver never chooses.

| set | arm | approve | fix_findings | recommended | free_text | override_offered_and_refused | prose_nudges | tasks with fix_findings | tasks with a refused override |
|---|---|---|---|---|---|---|---|---|---|
| paired | arm1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| paired | arm2 | 296 | 0 | 380 | 123 | 0 | 0 | 0 | 0 |
| paired | arm3 | 317 | 44 | 346 | 195 | 45 | 42 | 16 | 16 |
| all completed | arm1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| all completed | arm2 | 246 | 0 | 324 | 112 | 0 | 0 | 0 | 0 |
| all completed | arm3 | 280 | 31 | 327 | 137 | 32 | 17 | 13 | 13 |
