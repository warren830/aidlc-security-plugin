# CORS 通配符 + 允许凭证 — 修好版

## 场景

和 `cors-wildcard-credentials` 是同一处的修复：从请求里读 `Origin`，只在它属于显式 allowlist
时才回写 `Access-Control-Allow-Origin` 和 `Allow-Credentials`；不在 allowlist 里的源连 CORS 头
都拿不到，浏览器据此阻断跨源读取。这是 `cors-wildcard-credentials` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的 CORS 配置 finding。

## 现在的实现能否检测到

放行，符合预期。Continuum 没有报出 HIGH 及以上的 finding，插件门禁不拦。插件和 core 没有 security 类 sensor 覆盖 `src/cors.ts`，离线的本地检查看不到它。与 `cors-wildcard-credentials` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-91115f6b-a01d-46e5-bd16-25089437a38b`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它没有报出任何 finding。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/cors.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "CORS 通配符 + 允许凭证 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "cors-wildcard-credentials",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/cors.ts"
  ]
}
```
