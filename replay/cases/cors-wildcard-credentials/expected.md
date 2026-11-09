# CORS 通配符 + 允许凭证

## 场景

`src/cors.ts` 的 `handlePreflight` 把 `Access-Control-Allow-Origin` 设成 `*`，又把
`Access-Control-Allow-Credentials` 设成 `true`。现代浏览器虽然会拒绝 `*` + credentials 的组合，
但这一类配置在实践中经常被换成"反射 Origin 头"的形式重新出现，最终效果一样：任意网站都能
带用户凭证读接口。CWE-942（Permissive Cross-domain Policy）。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

待补。插件和 core 没有 security 类 sensor 覆盖 `src/cors.ts`，离线的本地检查看不到它。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case cors-wildcard-credentials` 之后写入。
与 `cors-wildcard-credentials-fixed` 成对。

## 证据

`bun replay/run.ts` 离线复验：对 `src/cors.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "CORS 通配符 + 允许凭证",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "pair": "cors-wildcard-credentials-fixed",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/cors.ts"
  ]
}
```
