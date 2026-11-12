# 验证测试套件报告

由 `bun replay/run.ts` 生成，不要手改。用例和预期见 `replay/cases/*/expected.md`。
Continuum 的结果来自 `bun replay/continuum.ts` 对真实 AWS Continuum 跑的差分 code review，记录在各用例的
`security-scan-result.md`。CI 不调用 AWS，只用插件门禁重新判一遍这些真实记录。

共 31 个用例：20 个有问题的版本，11 个修好的版本。

## 拦截率和误报率

插件开是这个仓库的完整流程，插件关是只有 AI-DLC core 的情况，两列来自同一次运行，定义见"插件开和关"。

| 指标 | 插件关 | 插件开 |
| --- | --- | --- |
| 拦截率：有问题的版本被拦下 | 0 / 20 | 19 / 20 |
| 误报率：修好的版本被误拦 | 0 / 11 | 0 / 11 |

插件开时每对场景两边的结果：

| 成对场景 | 有问题版 | 修好版 |
| --- | --- | --- |
| 命令注入（child_process.exec 拼接） | Continuum 检测到 | 放行（修好版） |
| CORS 通配符 + 允许凭证 | Continuum 检测到 | 放行（修好版） |
| Dockerfile：漂移的 latest 标签 + root 运行 | Continuum 检测到 | 放行（修好版） |
| 不安全的随机数（Math.random 生成 token） | Continuum 检测到 | 放行（修好版） |
| JWT 算法混淆（接受 alg: none） | Continuum 检测到 | 放行（修好版） |
| 路径穿越（fs.readFile + path.join） | Continuum 检测到 | 放行（修好版） |
| 凭证写进日志 | Continuum 检测到 | 放行（修好版） |
| 服务端请求伪造（SSRF） | Continuum 检测到 | 放行（修好版） |
| HIGH 威胁没有缓解证据 | 威胁覆盖检查拦下 | 放行（修好版） |
| 弱口令哈希（MD5） | Continuum 检测到 | 放行（修好版） |
| 反射型 XSS（模板字符串拼接） | Continuum 检测到 | 放行（修好版） |

## 插件开和关

插件关：只运行 AI-DLC core 自己的检查。对用例文件运行 core 的 `category: security` sensor（core 有 0 个），
对威胁模型运行 core 的 `required-sections`，但不给插件的模板。不运行插件的门禁，也不做威胁覆盖检查，
所以 Continuum 的记录只在插件开时参与判定。插件开：再加上插件的 sensor、门禁、威胁覆盖检查和插件的模板，结果见"全部用例"。

| 测试向量 | 插件关 | 插件开 | 插件关时的证据 |
| --- | --- | --- | --- |
| 打开仓库就执行的 agent 配置 | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.claude/settings.json`；没有 security 类 sensor 覆盖 `.mcp.json`；没有 security 类 sensor 覆盖 `.vscode/tasks.json` |
| 命令注入（child_process.exec 拼接） | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/git.ts` |
| 命令注入 — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/git.ts` |
| CORS 通配符 + 允许凭证 | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/cors.ts` |
| CORS 通配符 + 允许凭证 — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/cors.ts` |
| Dockerfile：漂移的 latest 标签 + root 运行 | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `Dockerfile` |
| Dockerfile：漂移的 latest 标签 + root 运行 — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `Dockerfile` |
| 不安全的随机数（Math.random 生成 token） | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/tokens.ts` |
| 不安全的随机数 — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/tokens.ts` |
| JWT 算法混淆（接受 alg: none） | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/jwt.ts` |
| JWT 算法混淆 — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/jwt.ts` |
| lockfile 里的被劫持版本和陌生依赖 | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `package-lock.json`；没有 security 类 sensor 覆盖 `package.json` |
| MCP 配置文件里的凭证 | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.mcp.json` |
| 路径穿越（fs.readFile + path.join） | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/reports.ts` |
| 路径穿越 — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/reports.ts` |
| 依赖的 postinstall 脚本 | 未检测到 | 未检测到 | 没有 security 类 sensor 覆盖 `package.json`；没有 security 类 sensor 覆盖 `vendor/example-helper/package.json`；没有 security 类 sensor 覆盖 `vendor/example-helper/postinstall.js` |
| pull_request_target 和 issue 标题注入 | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.github/workflows/triage.yml` |
| 规则文件里的隐形 Unicode 指令 | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.cursor/rules/style.mdc`；没有 security 类 sensor 覆盖 `.kiro/steering/style.md` |
| 凭证写进日志 | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/handler.ts` |
| 凭证写进日志 — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/handler.ts` |
| SQL 注入 | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/users.ts` |
| 服务端请求伪造（SSRF） | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/preview.ts` |
| 服务端请求伪造 — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/preview.ts` |
| 威胁模型漏了 STRIDE 章节 | 未检测到 | 必备章节检查拦下 | 没有 security 类 sensor 覆盖 `src/jwt.ts`；必备章节检查（没有模板）放行 |
| HIGH 威胁没有缓解证据 | 未检测到 | 威胁覆盖检查拦下 | 没有 security 类 sensor 覆盖 `src/jwt.ts`；必备章节检查（没有模板）放行 |
| HIGH 威胁没有缓解证据 — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/jwt.ts`；必备章节检查（没有模板）放行 |
| 引用未固定 SHA 的 Action | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.github/workflows/build.yml` |
| 弱口令哈希（MD5） | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/passwords.ts` |
| 弱口令哈希 — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/passwords.ts` |
| 反射型 XSS（模板字符串拼接） | 未检测到 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/greeting.ts` |
| 反射型 XSS — 修好版 | 放行（修好版） | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/greeting.ts` |

## 全部用例

插件开时的结果。

| 测试向量 | 检测环节 | 当前结果 | 证据 |
| --- | --- | --- | --- |
| [打开仓库就执行的 agent 配置](cases/agent-config-autorun/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.claude/settings.json`；没有 security 类 sensor 覆盖 `.mcp.json`；没有 security 类 sensor 覆盖 `.vscode/tasks.json`；Continuum `cj-57dee867-17e2-4bb2-b2bc-4bb4b7088a65`（ap-southeast-1，2026-11-09）报了 3 条：HIGH CODE_INJECTION @ .vscode/tasks.json:1、HIGH CODE_INJECTION @ .vscode/tasks.json:1、MEDIUM CODE_INJECTION @ .mcp.json:1；门禁拦下：f-409b902c-ae0a-4ab8-8b3e-49ec0c26d0c6 (HIGH)、f-8053e941-2b9f-4948-bdfa-ad292f62b630 (HIGH) |
| [命令注入（child_process.exec 拼接）](cases/command-injection-exec/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/git.ts`；Continuum `cj-5c8d27e8-289a-4d68-9e44-664f1a8aef00`（ap-southeast-1，2026-11-09）报了 1 条：HIGH COMMAND_INJECTION @ src/git.ts:6；门禁拦下：f-90b44628-cd56-4571-b9d9-b6c77a33bea2 (HIGH) |
| [命令注入 — 修好版](cases/command-injection-exec-fixed/expected.md) | 代码生成门禁 | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/git.ts`；Continuum `cj-aca14d5d-3a11-48a9-b84d-2b6c06a1ca2d`（ap-southeast-1，2026-11-09）报了 0 条；门禁放行 |
| [CORS 通配符 + 允许凭证](cases/cors-wildcard-credentials/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/cors.ts`；Continuum `cj-83aa88e6-59be-4b27-8511-e136a832add3`（ap-southeast-1，2026-11-09）报了 1 条：HIGH SECURITY_MISCONFIGURATION @ src/cors.ts:10；门禁拦下：f-33498a67-679b-487c-89fb-7f9050014712 (HIGH) |
| [CORS 通配符 + 允许凭证 — 修好版](cases/cors-wildcard-credentials-fixed/expected.md) | 代码生成门禁 | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/cors.ts`；Continuum `cj-91115f6b-a01d-46e5-bd16-25089437a38b`（ap-southeast-1，2026-11-09）报了 0 条；门禁放行 |
| [Dockerfile：漂移的 latest 标签 + root 运行](cases/dockerfile-latest-root/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `Dockerfile`；Continuum `cj-4e5a0ddc-2c32-4cea-9ece-2c7f00d9ec7f`（ap-southeast-1，2026-11-09）报了 3 条：MEDIUM SECURITY_MISCONFIGURATION @ Dockerfile:4、MEDIUM SECURITY_MISCONFIGURATION @ Dockerfile:7、HIGH PRIVILEGE_ESCALATION @ Dockerfile:11；门禁拦下：f-d9e4da50-57d0-4877-9e6a-005c0b9d1fc7 (HIGH) |
| [Dockerfile：漂移的 latest 标签 + root 运行 — 修好版](cases/dockerfile-latest-root-fixed/expected.md) | CI | 放行（修好版） | 没有 security 类 sensor 覆盖 `Dockerfile`；Continuum `cj-3c3a44b9-a4b6-4797-8dbc-79c15588026a`（ap-southeast-1，2026-11-09）报了 1 条：LOW SECURITY_MISCONFIGURATION @ Dockerfile:12；门禁放行 |
| [不安全的随机数（Math.random 生成 token）](cases/insecure-randomness/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/tokens.ts`；Continuum `cj-4a0af396-dede-493e-ae42-753c1d08b243`（ap-southeast-1，2026-11-09）报了 1 条：HIGH CRYPTOGRAPHIC_VULNERABILITIES @ src/tokens.ts:4；门禁拦下：f-6ba5eea1-9bfd-41f4-8a35-a3de80bcb71f (HIGH) |
| [不安全的随机数 — 修好版](cases/insecure-randomness-fixed/expected.md) | 代码生成门禁 | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/tokens.ts`；Continuum `cj-50af2257-2bcd-49dc-8712-9506c8e6d9c7`（ap-southeast-1，2026-11-09）报了 0 条；门禁放行 |
| [JWT 算法混淆（接受 alg: none）](cases/jwt-none-alg/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/jwt.ts`；Continuum `cj-524ed438-93c5-49b2-83b6-eb50897ee967`（ap-southeast-1，2026-11-09）报了 2 条：CRITICAL JSON_WEB_TOKEN_VULNERABILITIES @ src/jwt.ts:12、CRITICAL JSON_WEB_TOKEN_VULNERABILITIES @ src/jwt.ts:12；门禁拦下：f-901508db-ebbc-484d-af5d-2d2244d6fa7c (CRITICAL)、f-ed783696-5737-46da-a191-fb9a41e764c4 (CRITICAL) |
| [JWT 算法混淆 — 修好版](cases/jwt-none-alg-fixed/expected.md) | 代码生成门禁 | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/jwt.ts`；Continuum `cj-c6893a77-05b4-4014-8a90-4b5a657c02e3`（ap-southeast-1，2026-11-09）报了 1 条：LOW JSON_WEB_TOKEN_VULNERABILITIES @ src/jwt.ts:25；门禁放行 |
| [lockfile 里的被劫持版本和陌生依赖](cases/lockfile-new-dependency/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `package-lock.json`；没有 security 类 sensor 覆盖 `package.json`；Continuum `cj-4549a304-de2f-409f-b6df-9241bc63f1a5`（ap-southeast-1，2026-11-09）报了 2 条：HIGH SECURITY_MISCONFIGURATION @ package-lock.json:14、HIGH CODE_INJECTION @ package-lock.json:23；门禁拦下：f-29c61b7f-871d-44ba-bb7e-62b439afae80 (HIGH)、f-595467f4-0ced-4e44-a48e-9ccbbe8aeb9b (HIGH) |
| [MCP 配置文件里的凭证](cases/mcp-config-credential/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.mcp.json`；Continuum `cj-232b1e97-cc1e-4b00-88ee-6ca29bfa09a1`（ap-southeast-1，2026-11-09）报了 2 条：HIGH OTHER @ .mcp.json:6、HIGH DEFAULT_CREDENTIALS @ .mcp.json:6；门禁拦下：f-1550e6e6-d949-40a8-8e16-6c7adfd4512b (HIGH)、f-3a24368f-6a8d-4c30-818c-724488e1e12e (HIGH) |
| [路径穿越（fs.readFile + path.join）](cases/path-traversal/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/reports.ts`；Continuum `cj-5c195f54-5cf7-4419-aa87-8887957753ac`（ap-southeast-1，2026-11-09）报了 1 条：HIGH PATH_TRAVERSAL @ src/reports.ts:9；门禁拦下：f-0bab57b9-623f-45ed-ac94-d0f07457c0ba (HIGH) |
| [路径穿越 — 修好版](cases/path-traversal-fixed/expected.md) | 代码生成门禁 | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/reports.ts`；Continuum `cj-ab6cb970-bc91-4b76-b4f8-982598dd2e04`（ap-southeast-1，2026-11-09）报了 0 条；门禁放行 |
| [依赖的 postinstall 脚本](cases/postinstall-script/expected.md) | CI | 未检测到 | 没有 security 类 sensor 覆盖 `package.json`；没有 security 类 sensor 覆盖 `vendor/example-helper/package.json`；没有 security 类 sensor 覆盖 `vendor/example-helper/postinstall.js`；Continuum `cj-d4673b60-ee67-480c-b64d-84f0fe524893`（ap-southeast-1，2026-11-09）报了 1 条：MEDIUM CODE_INJECTION @ vendor/example-helper/package.json:4；门禁放行 |
| [pull_request_target 和 issue 标题注入](cases/pr-target-title-injection/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.github/workflows/triage.yml`；Continuum `cj-111aceb1-326e-472f-87f2-0d410f7a6b7d`（ap-southeast-1，2026-11-09）报了 2 条：HIGH PRIVILEGE_ESCALATION @ .github/workflows/triage.yml:16、CRITICAL COMMAND_INJECTION @ .github/workflows/triage.yml:19；门禁拦下：f-0681b67b-b2fb-498f-8a06-f520a93c261c (HIGH)、f-61cfe730-2786-47d2-9238-62716fae2176 (CRITICAL) |
| [规则文件里的隐形 Unicode 指令](cases/rules-file-unicode/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.cursor/rules/style.mdc`；没有 security 类 sensor 覆盖 `.kiro/steering/style.md`；Continuum `cj-6433c732-b80e-4664-b22d-c9b0a731f5ed`（ap-southeast-1，2026-11-09）报了 1 条：HIGH CODE_INJECTION @ .cursor/rules/style.mdc:1；门禁拦下：f-c2d98e7c-d2fe-467f-8e37-da43dac79c7a (HIGH) |
| [凭证写进日志](cases/secret-in-logs/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/handler.ts`；Continuum `cj-9695a0cb-4178-40d9-8d6e-521cdfe589ce`（ap-southeast-1，2026-11-09）报了 1 条：HIGH INFORMATION_DISCLOSURE @ src/handler.ts:9；门禁拦下：f-270386cc-557d-491e-9298-ca7293ab93c7 (HIGH) |
| [凭证写进日志 — 修好版](cases/secret-in-logs-fixed/expected.md) | 代码生成门禁 | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/handler.ts`；Continuum `cj-575f0ad8-6b99-4dea-80cd-d28805742aee`（ap-southeast-1，2026-11-09）报了 0 条；门禁放行 |
| [SQL 注入](cases/sql-injection/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/users.ts`；Continuum `cj-a92c256f-4a89-41de-957e-0228dac69d6d`（ap-southeast-1，2026-11-09）报了 1 条：HIGH SQL_INJECTION @ src/users.ts:5；门禁拦下：f-dc04b1d9-e96a-4421-8edd-9659d380f7dc (HIGH) |
| [服务端请求伪造（SSRF）](cases/ssrf-fetch/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/preview.ts`；Continuum `cj-4be8bd14-e60e-4448-a6b1-2094d21d4eb5`（ap-southeast-1，2026-11-09）报了 3 条：HIGH SERVER_SIDE_REQUEST_FORGERY @ src/preview.ts:12、MEDIUM CROSS_SITE_SCRIPTING @ src/preview.ts:15、HIGH SERVER_SIDE_REQUEST_FORGERY @ src/preview.ts:12；门禁拦下：f-3222cd16-2c77-4fdf-8cec-0f4ebb8bf924 (HIGH)、f-e7fa4a06-6983-406d-8c26-fe25ebdb86e4 (HIGH) |
| [服务端请求伪造 — 修好版](cases/ssrf-fetch-fixed/expected.md) | 代码生成门禁 | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/preview.ts`；Continuum `cj-8d97f232-045e-47af-adb5-8fa14598f4b7`（ap-southeast-1，2026-11-09）报了 0 条；门禁放行 |
| [威胁模型漏了 STRIDE 章节](cases/threat-model-missing-section/expected.md) | 威胁建模 | 必备章节检查拦下 | 没有 security 类 sensor 覆盖 `src/jwt.ts`；Continuum `cj-c6893a77-05b4-4014-8a90-4b5a657c02e3`（ap-southeast-1，2026-11-09）报了 1 条：LOW JSON_WEB_TOKEN_VULNERABILITIES @ src/jwt.ts:25；门禁放行；威胁覆盖检查（coverage_mode block）放行；必备章节检查（模板 12 节）拦下：缺 `## Repudiation` |
| [HIGH 威胁没有缓解证据](cases/uncovered-threat/expected.md) | 代码生成门禁 | 威胁覆盖检查拦下 | 没有 security 类 sensor 覆盖 `src/jwt.ts`；Continuum `cj-c6893a77-05b4-4014-8a90-4b5a657c02e3`（ap-southeast-1，2026-11-09）报了 1 条：LOW JSON_WEB_TOKEN_VULNERABILITIES @ src/jwt.ts:25；门禁放行；威胁覆盖检查（coverage_mode block）拦下：T-002 (HIGH)；必备章节检查（模板 12 节）放行 |
| [HIGH 威胁没有缓解证据 — 修好版](cases/uncovered-threat-fixed/expected.md) | 代码生成门禁 | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/jwt.ts`；Continuum `cj-c6893a77-05b4-4014-8a90-4b5a657c02e3`（ap-southeast-1，2026-11-09）报了 1 条：LOW JSON_WEB_TOKEN_VULNERABILITIES @ src/jwt.ts:25；门禁放行；威胁覆盖检查（coverage_mode block）放行；必备章节检查（模板 12 节）放行 |
| [引用未固定 SHA 的 Action](cases/unpinned-action/expected.md) | CI | Continuum 检测到 | 没有 security 类 sensor 覆盖 `.github/workflows/build.yml`；Continuum `cj-25a2a2cb-cebe-419c-b04a-4bb04880409c`（ap-southeast-1，2026-11-09）报了 1 条：HIGH OTHER @ .github/workflows/build.yml:14；门禁拦下：f-d9545f10-915d-45fa-b760-96831d979447 (HIGH) |
| [弱口令哈希（MD5）](cases/weak-crypto-md5/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/passwords.ts`；Continuum `cj-b491b3bc-e771-488a-89d1-5023555b4ec8`（ap-southeast-1，2026-11-09）报了 1 条：HIGH CRYPTOGRAPHIC_VULNERABILITIES @ src/passwords.ts:4；门禁拦下：f-64515405-6b25-483b-8101-182ad8499844 (HIGH) |
| [弱口令哈希 — 修好版](cases/weak-crypto-md5-fixed/expected.md) | 代码生成门禁 | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/passwords.ts`；Continuum `cj-9c6c3079-858d-4835-9be3-252ee73ee717`（ap-southeast-1，2026-11-09）报了 0 条；门禁放行 |
| [反射型 XSS（模板字符串拼接）](cases/xss-template-literal/expected.md) | 代码生成门禁 | Continuum 检测到 | 没有 security 类 sensor 覆盖 `src/greeting.ts`；Continuum `cj-57ff77f1-b925-4854-a298-bb6e9a243f43`（ap-southeast-1，2026-11-09）报了 1 条：HIGH CROSS_SITE_SCRIPTING @ src/greeting.ts:12；门禁拦下：f-636f08f5-3bd6-483f-9c71-41c5c520ee3d (HIGH) |
| [反射型 XSS — 修好版](cases/xss-template-literal-fixed/expected.md) | 代码生成门禁 | 放行（修好版） | 没有 security 类 sensor 覆盖 `src/greeting.ts`；Continuum `cj-da806adf-c387-4088-8b94-459892161651`（ap-southeast-1，2026-11-09）报了 0 条；门禁放行 |

## 未检测到

- 依赖的 postinstall 脚本。建议补在：AWS-9 Action。

## 误拦

无。
