# 弱口令哈希 — 修好版

## 场景

和 `weak-crypto-md5` 是同一处的修复：用 Node 的 `scryptSync`，每个口令一个 16 字节随机盐，
显式指定代价因子 `N=16384`，输出编码里带上算法名、参数、盐和派生值。scrypt 是设计用来
拖慢暴力破解的内存困难哈希。这是 `weak-crypto-md5` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的弱加密 finding。

## 现在的实现能否检测到

待补。本用例与 `weak-crypto-md5` 成对，预期结果是 `not-detected`。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case weak-crypto-md5-fixed` 之后写入。

## 证据

`bun replay/run.ts` 离线复验：对 `src/passwords.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "弱口令哈希 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "weak-crypto-md5",
  "gap_owner": "plugin",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/passwords.ts"
  ]
}
```
