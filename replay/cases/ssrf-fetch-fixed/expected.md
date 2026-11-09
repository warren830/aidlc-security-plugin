# 服务端请求伪造 — 修好版

## 场景

和 `ssrf-fetch` 是同一处的修复：先用 `new URL()` 解析目标，再校验 scheme 必须是 `https:`、
hostname 必须在显式 allowlist 里。任何 loopback、link-local 或内网地址都会在 fetch 之前被
拒绝。这是 `ssrf-fetch` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的 SSRF finding。

## 现在的实现能否检测到

待补。本用例与 `ssrf-fetch` 成对，预期结果是 `not-detected`。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case ssrf-fetch-fixed` 之后写入。

## 证据

`bun replay/run.ts` 离线复验：对 `src/preview.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "服务端请求伪造 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "ssrf-fetch",
  "gap_owner": "plugin",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/",
    "https://aws.amazon.com/security/security-bulletins/rss/2026-127-aws/"
  ],
  "files": [
    "src/preview.ts"
  ]
}
```
