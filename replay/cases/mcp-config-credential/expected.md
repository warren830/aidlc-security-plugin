# MCP 配置文件里的凭证

## 场景

仓库提交的 `.mcp.json` 在 `env` 里写了 AWS 访问密钥。`repo/.mcp.json` 里的值是假的
（`AKIAEXAMPLEFAKEKEYZZ`），已加进 `.gitleaks.toml` 的 allowlist。出处是 GitGuardian 2026
报告：公开的 MCP 配置文件里发现了 24,008 个 secrets。

## 理论上应该在哪个环节被检测

代码生成门禁：这个文件是 unit 的 diff 新增的，diff scan 应该报出硬编码凭证。
文件不是 AI-DLC 生成的时候，由 CI 里的 secret 扫描兜底。

## 现在的实现能否检测到

需要 AWS。扫描这一步要调用 Security Agent。门禁这一侧用录制样本演示：样本里有一条
ACTIVE 的 CRITICAL finding，门禁应该拦下。没有任何 security 类 sensor 检查
`.mcp.json`，插件和本仓库的 CI 都没有 secret 扫描。

AWS 实测：检测到。2026-11-08 在 us-east-1 的 agent space `aidlc-bench` 上，对和 `repo/`
完全相同的文件跑了一次 code review（job `cj-50af3609-3fc2-4683-bddd-50929883d8d8`）。
它报出 finding `f-67467dad-d58a-4348-857e-4718d42cd0ed`：`DEFAULT_CREDENTIALS`，HIGH，置信度 HIGH，
ACTIVE，位置 `.mcp.json:7-8`，就是那对假密钥。真实等级是 HIGH，录制样本写的是 CRITICAL；门禁在 HIGH
就拦，所以结论不变。同一次扫描还报了 3 条：`uvx` 每次启动都拉取没固定校验的远程包并把密钥交给它
（`CODE_INJECTION`，HIGH）、MCP 注册没有最小权限（`PRIVILEGE_ESCALATION`，HIGH）、没有审计日志（LOW）。
这次是直接调用 `securityagent` API 跑的整库 code review，没有经过插件 Step 4b 的 MCP diff scan，
也不在插件默认的 ap-southeast-1。

## 证据

`bun replay/run.ts --check` 对 `repo/.mcp.json` 跑了所有覆盖它的 security 类 sensor，
又对录制样本跑了门禁 worker。实际结果和下面的 `expected` 不一致时，命令失败。输出见
`replay/REPORT.md` 里的对应行。

```json
{
  "vector": "MCP 配置文件里的凭证",
  "stage": "code-generation-gate",
  "expected": "needs-aws",
  "sources": ["https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/"],
  "files": [".mcp.json"],
  "record": "security-scan-result.md",
  "aws_run": {
    "result": "detected",
    "at": "2026-11-08",
    "region": "us-east-1",
    "code_review_job_id": "cj-50af3609-3fc2-4683-bddd-50929883d8d8",
    "findings": ["DEFAULT_CREDENTIALS HIGH at .mcp.json:7-8 (f-67467dad-d58a-4348-857e-4718d42cd0ed)"]
  }
}
```
