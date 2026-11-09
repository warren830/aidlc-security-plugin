# CORS 通配符 + 允许凭证 — 修好版

## 场景

和 `cors-wildcard-credentials` 是同一处的修复：从请求里读 `Origin`，只在它属于显式 allowlist
时才回写 `Access-Control-Allow-Origin` 和 `Allow-Credentials`；不在 allowlist 里的源连 CORS 头
都拿不到，浏览器据此阻断跨源读取。这是 `cors-wildcard-credentials` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的 CORS 配置 finding。

## 现在的实现能否检测到

待补。本用例与 `cors-wildcard-credentials` 成对，预期结果是 `not-detected`。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case cors-wildcard-credentials-fixed` 之后写入。

## 证据

`bun replay/run.ts` 离线复验：对 `src/cors.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "CORS 通配符 + 允许凭证 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "cors-wildcard-credentials",
  "gap_owner": "plugin",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/cors.ts"
  ]
}
```
