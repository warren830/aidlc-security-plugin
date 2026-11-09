# JWT 算法混淆 — 修好版

## 场景

和 `jwt-none-alg` 是同一处的修复：把算法固定成 `HS256`，重新计算 HMAC，并用 `timingSafeEqual`
比对签名。任何 `alg != HS256` 的 token（包括 `none`）都在解码 payload 之前被拒绝。这是
`jwt-none-alg` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的签名/算法混淆 finding。

## 现在的实现能否检测到

待补。本用例与 `jwt-none-alg` 成对，预期结果是 `not-detected`。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case jwt-none-alg-fixed` 之后写入。

## 证据

`bun replay/run.ts` 离线复验：对 `src/jwt.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "JWT 算法混淆 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "jwt-none-alg",
  "gap_owner": "plugin",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/jwt.ts"
  ]
}
```
