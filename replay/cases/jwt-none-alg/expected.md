# JWT 算法混淆（接受 alg: none）

## 场景

`src/jwt.ts` 的 `verifyJwt` 读 JWT header 的 `alg`，如果等于 `none` 就直接返回 payload，连签名
都不验。攻击者只要把任意 token 的 header 改成 `{"alg":"none"}` 并去掉签名段，就能伪造任意
身份。这是经典的 JWT 算法混淆漏洞（CWE-347，Improper Verification of Cryptographic Signature）。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

待补。插件和 core 没有 security 类 sensor 覆盖 `src/jwt.ts`，离线的本地检查看不到它。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case jwt-none-alg` 之后写入。
与 `jwt-none-alg-fixed` 成对。

## 证据

`bun replay/run.ts` 离线复验：对 `src/jwt.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "JWT 算法混淆（接受 alg: none）",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "pair": "jwt-none-alg-fixed",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/jwt.ts"
  ]
}
```
