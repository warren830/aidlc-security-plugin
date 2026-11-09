# 凭证写进日志 — 修好版

## 场景

和 `secret-in-logs` 是同一处的修复：日志里只保留非敏感字段。`token` 经过 `maskToken` 处理，
只保留末 4 位，其余用 `*` 代替——足够让人在排错时辨认是不是同一次调用，又不足以被拿来
重新鉴权。这是 `secret-in-logs` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的 secret-in-logs finding。

## 现在的实现能否检测到

待补。本用例与 `secret-in-logs` 成对，预期结果是 `not-detected`。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case secret-in-logs-fixed` 之后写入。

## 证据

`bun replay/run.ts` 离线复验：对 `src/handler.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "凭证写进日志 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "secret-in-logs",
  "gap_owner": "plugin",
  "sources": [
    "https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/"
  ],
  "files": [
    "src/handler.ts"
  ]
}
```
