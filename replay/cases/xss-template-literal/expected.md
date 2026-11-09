# 反射型 XSS（模板字符串拼接）

## 场景

`src/greeting.ts` 里的 `renderGreeting` 把 `req.query.name` 直接拼进 HTML 字符串。
攻击者只要让受害者点开 `/?name=<script>…</script>` 这样的链接，脚本就在受害者浏览器里跑。
Veracode 2025 的报告里 XSS 一项 AI 生成代码 86% 没防住，是 OWASP Top 10 里 LLM 失败率最高的类别之一。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent
diff scan，`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `src/greeting.ts`，离线的本地检查看不到它。与 `xss-template-literal-fixed` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-57ff77f1-b925-4854-a298-bb6e9a243f43`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-636f08f5-3bd6-483f-9c71-41c5c520ee3d`：HIGH，CROSS_SITE_SCRIPTING: Reflected XSS: renderGreeting interpolates unescaped req.query.name into HTML response，位置 `src/greeting.ts:12`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/greeting.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "反射型 XSS（模板字符串拼接）",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "pair": "xss-template-literal-fixed",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/",
    "https://genai.owasp.org/llm-top-10/"
  ],
  "files": [
    "src/greeting.ts"
  ]
}
```
