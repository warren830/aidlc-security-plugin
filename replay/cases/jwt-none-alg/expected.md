# JWT 算法混淆（接受 alg: none）

## 场景

`src/jwt.ts` 的 `verifyJwt` 读 JWT header 的 `alg`，如果等于 `none` 就直接返回 payload，连签名
都不验。攻击者只要把任意 token 的 header 改成 `{"alg":"none"}` 并去掉签名段，就能伪造任意
身份。这是经典的 JWT 算法混淆漏洞（CWE-347，Improper Verification of Cryptographic Signature）。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `src/jwt.ts`，离线的本地检查看不到它。与 `jwt-none-alg-fixed` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-524ed438-93c5-49b2-83b6-eb50897ee967`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-901508db-ebbc-484d-af5d-2d2244d6fa7c`：CRITICAL，JSON_WEB_TOKEN_VULNERABILITIES: verifyJwt accepts unsigned/forged JWTs (alg:none, no signature verification) — authentication bypass and privilege escalation，位置 `src/jwt.ts:12`。
- `f-ed783696-5737-46da-a191-fb9a41e764c4`：CRITICAL，JSON_WEB_TOKEN_VULNERABILITIES: verifyJwt returns the JWT payload without any signature verification, allowing full authentication bypass and role forgery，位置 `src/jwt.ts:12`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/jwt.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

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
