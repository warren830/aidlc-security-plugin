# 验证测试套件报告

由 `bun replay/run.ts` 生成，不要手改。用例和预期见 `replay/cases/*/expected.md`。
「当前结果」是离线测出的，CI 每次重测；「AWS 实测」是对真实 AWS Security Agent 跑过的记录，CI 不重跑。

共 8 个用例：检测到 0，未检测到 6，需要 AWS 2。

| 测试向量 | 检测环节 | 当前结果 | AWS 实测 | 证据 |
| --- | --- | --- | --- | --- |
| [打开仓库就执行的 agent 配置](cases/agent-config-autorun/expected.md) | CI | 未检测到 | 未跑 | 没有 security 类 sensor 覆盖 `.claude/settings.json`；没有 security 类 sensor 覆盖 `.mcp.json`；没有 security 类 sensor 覆盖 `.vscode/tasks.json` |
| [lockfile 里的被劫持版本和陌生依赖](cases/lockfile-new-dependency/expected.md) | CI | 未检测到 | 未跑 | 没有 security 类 sensor 覆盖 `package-lock.json`；没有 security 类 sensor 覆盖 `package.json` |
| [MCP 配置文件里的凭证](cases/mcp-config-credential/expected.md) | 代码生成门禁 | 需要 AWS | 检测到（2026-11-08，us-east-1，`cj-50af3609-3fc2-4683-bddd-50929883d8d8`：DEFAULT_CREDENTIALS HIGH at .mcp.json:7-8 (f-67467dad-d58a-4348-857e-4718d42cd0ed)） | 没有 security 类 sensor 覆盖 `.mcp.json`；门禁拦下录制样本：f-902 (CRITICAL) Hardcoded credential at .mcp.json:7-8 is ACTIVE |
| [依赖的 postinstall 脚本](cases/postinstall-script/expected.md) | CI | 未检测到 | 未跑 | 没有 security 类 sensor 覆盖 `package.json`；没有 security 类 sensor 覆盖 `vendor/example-helper/package.json`；没有 security 类 sensor 覆盖 `vendor/example-helper/postinstall.js` |
| [pull_request_target 和 issue 标题注入](cases/pr-target-title-injection/expected.md) | CI | 未检测到 | 未跑 | 没有 security 类 sensor 覆盖 `.github/workflows/triage.yml` |
| [规则文件里的隐形 Unicode 指令](cases/rules-file-unicode/expected.md) | CI | 未检测到 | 未跑 | 没有 security 类 sensor 覆盖 `.cursor/rules/style.mdc`；没有 security 类 sensor 覆盖 `.kiro/steering/style.md` |
| [SQL 注入](cases/sql-injection/expected.md) | 代码生成门禁 | 需要 AWS | 检测到（2026-11-08，us-east-1，`cj-a47ab279-7b95-4c51-9601-4df49c8d6527`：SQL_INJECTION HIGH at users.ts:6 (f-48befbf1-5da0-433e-923c-7db4086c2727)） | 没有 security 类 sensor 覆盖 `src/users.ts`；门禁拦下录制样本：f-901 (HIGH) SQL injection at src/users.ts:6 is ACTIVE |
| [引用未固定 SHA 的 Action](cases/unpinned-action/expected.md) | CI | 未检测到 | 未跑 | 没有 security 类 sensor 覆盖 `.github/workflows/build.yml` |

## 未检测到

- 打开仓库就执行的 agent 配置。建议补在：AWS-9 Action。
- lockfile 里的被劫持版本和陌生依赖。建议补在：AWS-9 Action。
- 依赖的 postinstall 脚本。建议补在：AWS-9 Action。
- pull_request_target 和 issue 标题注入。建议补在：AWS-9 Action。
- 规则文件里的隐形 Unicode 指令。建议补在：AWS-9 Action。
- 引用未固定 SHA 的 Action。建议补在：AWS-9 Action。
