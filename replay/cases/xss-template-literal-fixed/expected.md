# 反射型 XSS — 修好版

## 场景

和 `xss-template-literal` 是同一处的修复：`renderGreeting` 仍然把 `req.query.name` 写进 HTML，
但先过一个 `escapeHtml` 帮助函数，把 `& < > " '` 全部转成实体，攻击者注入的标记变成纯文本。
这是 `xss-template-literal` 的"干净对照"，用于测 Continuum 和门禁的误报率。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的 XSS finding；如果还报，
就是误报，需要回给 Continuum。

## 现在的实现能否检测到

放行，符合预期。Continuum 没有报出 HIGH 及以上的 finding，插件门禁不拦。插件和 core 没有 security 类 sensor 覆盖 `src/greeting.ts`，离线的本地检查看不到它。与 `xss-template-literal` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-da806adf-c387-4088-8b94-459892161651`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它没有报出任何 finding。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/greeting.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "反射型 XSS — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "xss-template-literal",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/",
    "https://genai.owasp.org/llm-top-10/"
  ],
  "files": [
    "src/greeting.ts"
  ]
}
```
