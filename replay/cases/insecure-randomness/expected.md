# 不安全的随机数（Math.random 生成 token）

## 场景

`src/tokens.ts` 的 `generateResetToken` 用 `Math.random()` 拼一个 32 字符的"重置密码 token"。
`Math.random` 用的是 V8 的 xorshift128+，不是密码学安全的随机源：知道几个输出就能推出状态，
进而预测后续 token。CWE-338（Use of Cryptographically Weak PRNG）。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `src/tokens.ts`，离线的本地检查看不到它。与 `insecure-randomness-fixed` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-4a0af396-dede-493e-ae42-753c1d08b243`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-6ba5eea1-9bfd-41f4-8a35-a3de80bcb71f`：HIGH，CRYPTOGRAPHIC_VULNERABILITIES: Password-reset token generated with non-cryptographic Math.random()，位置 `src/tokens.ts:4`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/tokens.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

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
