# SQL 注入

## 场景

生成的代码把请求参数直接拼进 SQL。`repo/src/users.ts` 是最小样本，
`findUser` 用模板字符串拼出查询。出处是 Veracode 2025 的报告：45% 的 AI 生成代码样本引入了 OWASP Top 10 漏洞。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security
Agent diff scan，`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `src/users.ts`，离线的本地检查看不到它。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的
AWS Continuum 差分 code review（job `cj-a92c256f-4a89-41de-957e-0228dac69d6d`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-dc04b1d9-e96a-4421-8edd-9659d380f7dc`：HIGH，SQL_INJECTION: findUser interpolates untrusted `name` into SQL string literal (SQL injection)，位置 `src/users.ts:5`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/users.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "SQL 注入",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/users.ts"
  ]
}
```
