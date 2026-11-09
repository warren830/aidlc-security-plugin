# 不安全的随机数（Math.random 生成 token）

## 场景

`src/tokens.ts` 的 `generateResetToken` 用 `Math.random()` 拼一个 32 字符的"重置密码 token"。
`Math.random` 用的是 V8 的 xorshift128+，不是密码学安全的随机源：知道几个输出就能推出状态，
进而预测后续 token。CWE-338（Use of Cryptographically Weak PRNG）。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

待补。插件和 core 没有 security 类 sensor 覆盖 `src/tokens.ts`，离线的本地检查看不到它。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case insecure-randomness` 之后写入。
与 `insecure-randomness-fixed` 成对。

## 证据

`bun replay/run.ts` 离线复验：对 `src/tokens.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "不安全的随机数（Math.random 生成 token）",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "pair": "insecure-randomness-fixed",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/tokens.ts"
  ]
}
```
