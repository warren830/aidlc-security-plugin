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

待补。插件和 core 没有 security 类 sensor 覆盖 `src/handler.ts`，离线的本地检查看不到它。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case secret-in-logs` 之后写入。
与 `secret-in-logs-fixed` 成对。

## 证据

`bun replay/run.ts` 离线复验：对 `src/handler.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

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
