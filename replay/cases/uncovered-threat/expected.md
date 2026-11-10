# HIGH 威胁没有缓解证据

## 场景

威胁模型给 JWT 校验列了两条 HIGH 及以上的威胁：`T-001`（CRITICAL，header 写 `alg: none` 或别的算法、
签名不对也照样接受的 token）和 `T-002`（HIGH，已经过期、或者签发方和接收方不是本服务的 token 照样接受）。
代码和 `jwt-none-alg-fixed` 一样，两条都处理了。但 Code Generation 的 Step 4c 只在 `threat_coverage`
里登记了 `T-001` 的证据，漏了 `T-002`，扫描记录说不出哪段代码对应它。

## 理论上应该在哪个环节被检测

代码生成门禁。`security-findings-gate` 的威胁覆盖检查要求威胁模型里每条 HIGH 及以上的威胁，在扫描记录的
`threat_coverage` 里都有一条：缓解它的代码或测试、人对风险的接受，或者它不适用于这个 unit 的理由。

## 现在的实现能否检测到

威胁覆盖检查拦下。用例的 `.aidlc-security.json` 设了 `"coverage_mode": "block"`，`T-002` 没有条目，门禁拦下。
默认的 `warn` 只在 `coverage_gaps` 里列出，不拦。与 `uncovered-threat-fixed` 成对。

`security-threat-model.md` 是手写的，没有跑过真实的 AWS Security Agent 威胁模型 review，它的 `scan_id` 是
`hand-written`。`repo/` 和 `security-scan-result.md` 原样复制自 `jwt-none-alg-fixed`：同一份代码，同一次
Continuum 真实结果（job `cj-c6893a77-05b4-4014-8a90-4b5a657c02e3`），只报了一条 LOW，门禁按 finding 放行。
`threat-coverage.json` 是 agent 在 Step 4c 会写进记录的 `threat_coverage`。

## 证据

`bun replay/run.ts --check` 先像别的用例一样判 `security-scan-result.md`，再在临时目录里搭一个记录目录：
`security-threat-model.md` 放在 `<record>/inception/security-threat-model/`，扫描记录放在
`<record>/construction/uncovered-threat/code-generation/`，`threat-coverage.json` 合进记录的 `json` 块，
`schema_version` 改成 2。门禁在用例目录下运行，读这里的 `.aidlc-security.json`。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "HIGH 威胁没有缓解证据",
  "stage": "code-generation-gate",
  "expected": "coverage",
  "pair": "uncovered-threat-fixed",
  "sources": [
    "https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html",
    "https://www.rfc-editor.org/rfc/rfc8725"
  ],
  "files": [
    "src/jwt.ts"
  ]
}
```
