# 弱口令哈希（MD5）

## 场景

`src/passwords.ts` 的 `hashPassword` 用 `crypto.createHash("md5")` 给密码做哈希。MD5 是通用摘要，
既不是慢哈希也不加盐：泄漏数据库后，攻击者可以用彩虹表和字典在离线环境几十亿次/秒地试。
OWASP A02（加密机制失效）和 CWE-327（Use of a Broken or Risky Cryptographic Algorithm）。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

待补。插件和 core 没有 security 类 sensor 覆盖 `src/passwords.ts`，离线的本地检查看不到它。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case weak-crypto-md5` 之后写入。
与 `weak-crypto-md5-fixed` 成对。

## 证据

`bun replay/run.ts` 离线复验：对 `src/passwords.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

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
