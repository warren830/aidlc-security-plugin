# 反射型 XSS（模板字符串拼接）

## 场景

`src/greeting.ts` 里的 `renderGreeting` 把 `req.query.name` 直接拼进 HTML 字符串。
攻击者只要让受害者点开 `/?name=<script>…</script>` 这样的链接，脚本就在受害者浏览器里跑。
Veracode 2025 的报告里 XSS 一项 AI 生成代码 86% 没防住，是 OWASP Top 10 里 LLM 失败率最高的类别之一。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent
diff scan，`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

待补。插件和 core 没有 security 类 sensor 覆盖 `src/greeting.ts`，离线的本地检查看不到它。
Continuum 这一侧待跑：本用例还没有 `security-scan-result.md`，由开发·EC2 跑完
`bun replay/continuum.ts --case xss-template-literal` 之后写入。本用例与
`xss-template-literal-fixed` 是同一漏洞的"有问题版 / 修好版"成对样例，修好版用于测误报率。

## 证据

`bun replay/run.ts` 离线复验：对 `src/greeting.ts` 跑所有覆盖它的 security 类 sensor（预期无覆盖），
再用插件的 `security-findings-gate` 判 `security-scan-result.md`。Continuum 跑完后
本文件的"现在的实现能否检测到"一节会改成实测结论。

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
