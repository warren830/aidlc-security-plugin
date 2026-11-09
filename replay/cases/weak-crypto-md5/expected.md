# 弱口令哈希（MD5）

## 场景

`src/passwords.ts` 的 `hashPassword` 用 `crypto.createHash("md5")` 给密码做哈希。MD5 是通用摘要，
既不是慢哈希也不加盐：泄漏数据库后，攻击者可以用彩虹表和字典在离线环境几十亿次/秒地试。
OWASP A02（加密机制失效）和 CWE-327（Use of a Broken or Risky Cryptographic Algorithm）。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `src/passwords.ts`，离线的本地检查看不到它。与 `weak-crypto-md5-fixed` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-b491b3bc-e771-488a-89d1-5023555b4ec8`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-64515405-6b25-483b-8101-182ad8499844`：HIGH，CRYPTOGRAPHIC_VULNERABILITIES: hashPassword() uses unsalted MD5 for password storage，位置 `src/passwords.ts:4`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/passwords.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "弱口令哈希（MD5）",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "pair": "weak-crypto-md5-fixed",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/passwords.ts"
  ]
}
```
