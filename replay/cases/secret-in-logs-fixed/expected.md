# 凭证写进日志 — 修好版

## 场景

和 `secret-in-logs` 是同一处的修复：日志里只保留非敏感字段。`token` 经过 `maskToken` 处理，
只保留末 4 位，其余用 `*` 代替——足够让人在排错时辨认是不是同一次调用，又不足以被拿来
重新鉴权。这是 `secret-in-logs` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的 secret-in-logs finding。

## 现在的实现能否检测到

放行，符合预期。Continuum 没有报出 HIGH 及以上的 finding，插件门禁不拦。插件和 core 没有 security 类 sensor 覆盖 `src/handler.ts`，离线的本地检查看不到它。与 `secret-in-logs` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-575f0ad8-6b99-4dea-80cd-d28805742aee`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它没有报出任何 finding。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/handler.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "凭证写进日志 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "secret-in-logs",
  "sources": [
    "https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/"
  ],
  "files": [
    "src/handler.ts"
  ]
}
```
