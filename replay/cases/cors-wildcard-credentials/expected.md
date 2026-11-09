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

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `src/cors.ts`，离线的本地检查看不到它。与 `cors-wildcard-credentials-fixed` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-83aa88e6-59be-4b27-8511-e136a832add3`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-33498a67-679b-487c-89fb-7f9050014712`：HIGH，SECURITY_MISCONFIGURATION: handlePreflight emits wildcard Access-Control-Allow-Origin with Access-Control-Allow-Credentials: true, no Origin allowlist or Vary，位置 `src/cors.ts:10`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/cors.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

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
