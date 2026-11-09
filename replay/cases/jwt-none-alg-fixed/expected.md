# JWT 算法混淆 — 修好版

## 场景

和 `jwt-none-alg` 是同一处的修复：把算法固定成 `HS256`，重新计算 HMAC，并用 `timingSafeEqual`
比对签名。任何 `alg != HS256` 的 token（包括 `none`）都在解码 payload 之前被拒绝。验签之后
还校验 `typ`、`exp`、`iss` 和 `aud`。这是 `jwt-none-alg` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的签名/算法混淆 finding。

## 现在的实现能否检测到

放行，符合预期。Continuum 没有报出 HIGH 及以上的 finding，插件门禁不拦。插件和 core 没有 security 类 sensor 覆盖 `src/jwt.ts`，离线的本地检查看不到它。与 `jwt-none-alg` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-c6893a77-05b4-4014-8a90-4b5a657c02e3`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-a921798c-b84f-406e-8d5c-929afe5e4a91`：LOW，JSON_WEB_TOKEN_VULNERABILITIES: Hand-rolled JWT verification instead of established library，位置 `src/jwt.ts:25`。

第一版修复没过：Continuum 在 job `cj-82f667ce-8a98-4bb9-a600-33d33e100791` 里报出 HIGH JSON_WEB_TOKEN_VULNERABILITIES：只验签名，不校验 exp、iss、aud、typ，泄露或过期的 token 会一直有效。这是真实的残留问题，不是误报。补全修复（加上 typ、exp、iss、aud 校验）后重新扫描，结果如上。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/jwt.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "JWT 算法混淆 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "jwt-none-alg",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/jwt.ts"
  ]
}
```
