# 反射型 XSS — 修好版

## 场景

和 `xss-template-literal` 是同一处的修复：`renderGreeting` 仍然把 `req.query.name` 写进 HTML，
但先过一个 `escapeHtml` 帮助函数，把 `& < > " '` 全部转成实体，攻击者注入的标记变成纯文本。
这是 `xss-template-literal` 的"干净对照"，用于测 Continuum 和门禁的误报率。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的 XSS finding；如果还报，
就是误报，需要回给 Continuum。

## 现在的实现能否检测到

待补。本用例与 `xss-template-literal` 成对，预期结果是 `not-detected`（即门禁不应再拦）。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case xss-template-literal-fixed` 之后写入。
如果实测 Continuum 仍然报 HIGH 及以上，那是误报，要在这里和 REPORT 里如实记录。

## 证据

`bun replay/run.ts` 离线复验：对 `src/greeting.ts` 跑所有覆盖它的 security 类 sensor，
再用插件的 `security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "反射型 XSS — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "xss-template-literal",
  "gap_owner": "plugin",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/",
    "https://genai.owasp.org/llm-top-10/"
  ],
  "files": [
    "src/greeting.ts"
  ]
}
```
