# 验证测试套件报告

由 `bun replay/run.ts` 生成，不要手改。用例和预期见 `replay/cases/*/expected.md`。
Continuum 的结果来自 `bun replay/continuum.ts` 对真实 AWS Continuum 跑的差分 code review，记录在各用例的
`security-scan-result.md`。CI 不调用 AWS，只用插件门禁重新判一遍这些真实记录。

共 8 个用例：本地检测到 0，Continuum 检测到 7，未检测到 1。

| 测试向量 | 检测环节 | 当前结果 | 证据 |
| --- | --- | --- | --- |
| [打开仓库就执行的 agent 配置](cases/agent-config-autorun/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.claude/settings.json`；没有 security 类 sensor 覆盖 `.mcp.json`；没有 security 类 sensor 覆盖 `.vscode/tasks.json`；Continuum `cj-57dee867-17e2-4bb2-b2bc-4bb4b7088a65`（ap-southeast-1，2026-11-09）报了 3 条：HIGH CODE_INJECTION @ .vscode/tasks.json:1、HIGH CODE_INJECTION @ .vscode/tasks.json:1、MEDIUM CODE_INJECTION @ .mcp.json:1；门禁拦下：f-409b902c-ae0a-4ab8-8b3e-49ec0c26d0c6 (HIGH)、f-8053e941-2b9f-4948-bdfa-ad292f62b630 (HIGH) |
| [lockfile 里的被劫持版本和陌生依赖](cases/lockfile-new-dependency/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `package-lock.json`；没有 security 类 sensor 覆盖 `package.json`；Continuum `cj-4549a304-de2f-409f-b6df-9241bc63f1a5`（ap-southeast-1，2026-11-09）报了 2 条：HIGH SECURITY_MISCONFIGURATION @ package-lock.json:14、HIGH CODE_INJECTION @ package-lock.json:23；门禁拦下：f-29c61b7f-871d-44ba-bb7e-62b439afae80 (HIGH)、f-595467f4-0ced-4e44-a48e-9ccbbe8aeb9b (HIGH) |
| [MCP 配置文件里的凭证](cases/mcp-config-credential/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.mcp.json`；Continuum `cj-232b1e97-cc1e-4b00-88ee-6ca29bfa09a1`（ap-southeast-1，2026-11-09）报了 2 条：HIGH OTHER @ .mcp.json:6、HIGH DEFAULT_CREDENTIALS @ .mcp.json:6；门禁拦下：f-1550e6e6-d949-40a8-8e16-6c7adfd4512b (HIGH)、f-3a24368f-6a8d-4c30-818c-724488e1e12e (HIGH) |
| [依赖的 postinstall 脚本](cases/postinstall-script/expected.md) | CI | 未检测到 | 没有 security 类 sensor 覆盖 `package.json`；没有 security 类 sensor 覆盖 `vendor/example-helper/package.json`；没有 security 类 sensor 覆盖 `vendor/example-helper/postinstall.js`；Continuum `cj-d4673b60-ee67-480c-b64d-84f0fe524893`（ap-southeast-1，2026-11-09）报了 1 条：MEDIUM CODE_INJECTION @ vendor/example-helper/package.json:4；门禁放行 |
| [pull_request_target 和 issue 标题注入](cases/pr-target-title-injection/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.github/workflows/triage.yml`；Continuum `cj-111aceb1-326e-472f-87f2-0d410f7a6b7d`（ap-southeast-1，2026-11-09）报了 2 条：HIGH PRIVILEGE_ESCALATION @ .github/workflows/triage.yml:16、CRITICAL COMMAND_INJECTION @ .github/workflows/triage.yml:19；门禁拦下：f-0681b67b-b2fb-498f-8a06-f520a93c261c (HIGH)、f-61cfe730-2786-47d2-9238-62716fae2176 (CRITICAL) |
| [规则文件里的隐形 Unicode 指令](cases/rules-file-unicode/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.cursor/rules/style.mdc`；没有 security 类 sensor 覆盖 `.kiro/steering/style.md`；Continuum `cj-6433c732-b80e-4664-b22d-c9b0a731f5ed`（ap-southeast-1，2026-11-09）报了 1 条：HIGH CODE_INJECTION @ .cursor/rules/style.mdc:1；门禁拦下：f-c2d98e7c-d2fe-467f-8e37-da43dac79c7a (HIGH) |
| [SQL 注入](cases/sql-injection/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/users.ts`；Continuum `cj-a92c256f-4a89-41de-957e-0228dac69d6d`（ap-southeast-1，2026-11-09）报了 1 条：HIGH SQL_INJECTION @ src/users.ts:5；门禁拦下：f-dc04b1d9-e96a-4421-8edd-9659d380f7dc (HIGH) |
| [引用未固定 SHA 的 Action](cases/unpinned-action/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.github/workflows/build.yml`；Continuum `cj-25a2a2cb-cebe-419c-b04a-4bb04880409c`（ap-southeast-1，2026-11-09）报了 1 条：HIGH OTHER @ .github/workflows/build.yml:14；门禁拦下：f-d9545f10-915d-45fa-b760-96831d979447 (HIGH) |

## 未检测到

- 依赖的 postinstall 脚本。建议补在：AWS-9 Action。
