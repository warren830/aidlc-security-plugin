# 不安全的随机数 — 修好版

## 场景

和 `insecure-randomness` 是同一处的修复：用 Node 的 `crypto.randomBytes(32)` 取 32 字节熵，
用 base64url 编码输出。底层是操作系统的 CSPRNG，攻击者无法通过已知输出预测后续 token。
这是 `insecure-randomness` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的弱随机 finding。

## 现在的实现能否检测到

放行，符合预期。Continuum 没有报出 HIGH 及以上的 finding，插件门禁不拦。插件和 core 没有 security 类 sensor 覆盖 `src/tokens.ts`，离线的本地检查看不到它。与 `insecure-randomness` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-50af2257-2bcd-49dc-8712-9506c8e6d9c7`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它没有报出任何 finding。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/tokens.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "不安全的随机数 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "insecure-randomness",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/tokens.ts"
  ]
}
```
