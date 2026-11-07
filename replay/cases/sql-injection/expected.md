# SQL 注入

## 场景

生成的代码把请求参数直接拼进 SQL。`repo/src/users.ts` 是最小样本，
`findUser` 用模板字符串拼出查询。出处是 Veracode 2025 的报告：45% 的 AI 生成代码样本引入了 OWASP Top 10 漏洞。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security
Agent diff scan，`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

需要 AWS。扫描这一步要调用 Security Agent，离线跑不了。门禁这一侧用录制样本
`security-scan-result.md` 演示：样本里有一条 ACTIVE 的 HIGH finding，门禁应该拦下。
没有任何 security 类 sensor 直接检查 `src/users.ts`。

## 证据

`bun replay/run.ts --check` 对 `repo/src/users.ts` 跑了所有覆盖它的 security 类
sensor，又对录制样本跑了门禁 worker。实际结果和下面的 `expected` 不一致时，
命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "SQL 注入",
  "stage": "code-generation-gate",
  "expected": "needs-aws",
  "sources": ["https://www.veracode.com/blog/genai-code-security-report/"],
  "files": ["src/users.ts"],
  "record": "security-scan-result.md"
}
```
