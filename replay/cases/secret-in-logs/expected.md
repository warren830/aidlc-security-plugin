# 凭证写进日志

## 场景

`src/handler.ts` 的 `handleRequest` 把整个 `AuthContext` 直接交给 `console.log`，包括调用方的
bearer token。生产环境的应用日志通常会被集中收集（CloudWatch、ELK、Splunk），能读日志的人
远超能读 secret 的人，等于把凭证外溢到一个权限更宽的面。CWE-532（Insertion of Sensitive
Information into Log File）和 GitGuardian 的 secrets sprawl 报告都反复提到这一类。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `src/handler.ts`，离线的本地检查看不到它。与 `secret-in-logs-fixed` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-9695a0cb-4178-40d9-8d6e-521cdfe589ce`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-270386cc-557d-491e-9298-ca7293ab93c7`：HIGH，INFORMATION_DISCLOSURE: Bearer token logged in plaintext via console.log in handleRequest (CWE-532)，位置 `src/handler.ts:9`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/handler.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "凭证写进日志",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "pair": "secret-in-logs-fixed",
  "sources": [
    "https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/"
  ],
  "files": [
    "src/handler.ts"
  ]
}
```
