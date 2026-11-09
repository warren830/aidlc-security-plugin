# 命令注入 — 修好版

## 场景

和 `command-injection-exec` 是同一处的修复：用 `execFile("git", ["checkout", branch])` 替代 `exec`。
`execFile` 不走 shell，参数按数组逐项传递，`branch` 里的元字符变成普通字面量。这是
`command-injection-exec` 的干净对照，用于测误报率。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的命令注入 finding。

## 现在的实现能否检测到

待补。本用例与 `command-injection-exec` 成对，预期结果是 `not-detected`。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case command-injection-exec-fixed` 之后写入。

## 证据

`bun replay/run.ts` 离线复验：对 `src/git.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "命令注入 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "command-injection-exec",
  "gap_owner": "plugin",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/",
    "https://www.wiz.io/blog/red-agent-snowflake-copilot-cicd-bug"
  ],
  "files": [
    "src/git.ts"
  ]
}
```
