# HIGH 威胁没有缓解证据 — 修好版

## 场景

和 `uncovered-threat` 是同一份代码、同一份威胁模型，修好的是扫描记录：Step 4c 给 `T-001` 和 `T-002`
都登记了证据。`T-001` 指向 `src/jwt.ts` 里固定 HS256、比对签名的那段（第 25 到 33 行），`T-002` 指向校验
`exp`、`iss` 和 `aud` 的那段（第 35 到 41 行）。`T-003` 是 MEDIUM，低于门禁阈值，不用登记。

## 理论上应该在哪个环节被检测

代码生成门禁。威胁模型里每条 HIGH 及以上的威胁都有证据，威胁覆盖检查应该放行。

## 现在的实现能否检测到

放行，符合预期。`coverage_mode` 是 `block`，两条威胁都有证据，门禁不拦。与 `uncovered-threat` 成对。

`security-threat-model.md` 是手写的，没有跑过真实的 AWS Security Agent 威胁模型 review，它的 `scan_id` 是
`hand-written`。`repo/` 和 `security-scan-result.md` 原样复制自 `jwt-none-alg-fixed`：同一份代码，同一次
Continuum 真实结果（job `cj-c6893a77-05b4-4014-8a90-4b5a657c02e3`），只报了一条 LOW。`threat-coverage.json`
是 agent 在 Step 4c 会写进记录的 `threat_coverage`。

## 证据

和 `uncovered-threat` 一样，`bun replay/run.ts --check` 先判 `security-scan-result.md`，再把合进
`threat-coverage.json`、`schema_version` 改成 2 的记录放进临时记录目录，在用例目录下运行门禁。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "HIGH 威胁没有缓解证据 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "uncovered-threat",
  "sources": [
    "https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html",
    "https://www.rfc-editor.org/rfc/rfc8725"
  ],
  "files": [
    "src/jwt.ts"
  ]
}
```
