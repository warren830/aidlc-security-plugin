# 不安全的随机数 — 修好版

## 场景

和 `insecure-randomness` 是同一处的修复：用 Node 的 `crypto.randomBytes(32)` 取 32 字节熵，
用 base64url 编码输出。底层是操作系统的 CSPRNG，攻击者无法通过已知输出预测后续 token。
这是 `insecure-randomness` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的弱随机 finding。

## 现在的实现能否检测到

待补。本用例与 `insecure-randomness` 成对，预期结果是 `not-detected`。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case insecure-randomness-fixed` 之后写入。

## 证据

`bun replay/run.ts` 离线复验：对 `src/tokens.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "不安全的随机数 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "insecure-randomness",
  "gap_owner": "plugin",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/tokens.ts"
  ]
}
```
