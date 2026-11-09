# MCP 配置文件里的凭证

## 场景

仓库提交的 `.mcp.json` 在 `env` 里写了 AWS 访问密钥。`repo/.mcp.json` 里的值是假的
（`AKIAEXAMPLEFAKEKEYZZ`），已加进 `.gitleaks.toml` 的 allowlist。出处是 GitGuardian 2026
报告：公开的 MCP 配置文件里发现了 24,008 个 secrets。

## 理论上应该在哪个环节被检测

代码生成门禁：这个文件是 unit 的 diff 新增的，diff scan 应该报出硬编码凭证。
文件不是 AI-DLC 生成的时候，由 CI 里的 secret 扫描兜底。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `.mcp.json`，离线的本地检查看不到它。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的
AWS Continuum 差分 code review（job `cj-232b1e97-cc1e-4b00-88ee-6ca29bfa09a1`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-1550e6e6-d949-40a8-8e16-6c7adfd4512b`：HIGH，OTHER: Hardcoded AWS credentials committed in new .mcp.json，位置 `.mcp.json:6`。
- `f-3a24368f-6a8d-4c30-818c-724488e1e12e`：HIGH，DEFAULT_CREDENTIALS: AWS access key ID and secret key committed in plaintext in .mcp.json, exposing cloud credentials to anyone with repo access，位置 `.mcp.json:6`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `.mcp.json` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "MCP 配置文件里的凭证",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "sources": [
    "https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/"
  ],
  "files": [
    ".mcp.json"
  ]
}
```
