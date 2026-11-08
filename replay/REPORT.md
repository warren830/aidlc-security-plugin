# 验证测试套件报告

由 `bun replay/run.ts` 生成，不要手改。用例和预期见 `replay/cases/*/expected.md`。
「当前结果」是离线测出的，CI 每次重测；「AWS 实测」是对真实 AWS Security Agent 跑过的记录，CI 不重跑。

共 3 个用例：检测到 0，未检测到 1，需要 AWS 2。

| 测试向量 | 检测环节 | 当前结果 | AWS 实测 | 证据 |
| --- | --- | --- | --- | --- |
| [MCP 配置文件里的凭证](cases/mcp-config-credential/expected.md) | 代码生成门禁 | 需要 AWS | 检测到（2026-11-08，us-east-1，`cj-50af3609-3fc2-4683-bddd-50929883d8d8`：DEFAULT_CREDENTIALS HIGH at .mcp.json:7-8 (f-67467dad-d58a-4348-857e-4718d42cd0ed)） | 没有 security 类 sensor 覆盖 `.mcp.json`；门禁拦下录制样本：f-902 (CRITICAL) Hardcoded credential at .mcp.json:7-8 is ACTIVE |
| [SQL 注入](cases/sql-injection/expected.md) | 代码生成门禁 | 需要 AWS | 检测到（2026-11-08，us-east-1，`cj-a47ab279-7b95-4c51-9601-4df49c8d6527`：SQL_INJECTION HIGH at users.ts:6 (f-48befbf1-5da0-433e-923c-7db4086c2727)） | 没有 security 类 sensor 覆盖 `src/users.ts`；门禁拦下录制样本：f-901 (HIGH) SQL injection at src/users.ts:6 is ACTIVE |
| [引用未固定 SHA 的 Action](cases/unpinned-action/expected.md) | CI | 未检测到 | 未跑 | 没有 security 类 sensor 覆盖 `.github/workflows/build.yml` |

## 未检测到

- 引用未固定 SHA 的 Action。建议补在：AWS-9 Action。
