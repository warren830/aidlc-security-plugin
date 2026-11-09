# 命令注入（child_process.exec 拼接）

## 场景

`src/git.ts` 的 `checkoutBranch` 用 `exec` 跑 `git checkout ${branch}`。`exec` 把整条字符串交给 shell 解析，
`branch` 里的 `;`、`&&`、反引号或 `$()` 都会被求值，等价于让远端输入直接进 shell。这是 OWASP A03
注入里最常见的一类。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

待补。插件和 core 没有 security 类 sensor 覆盖 `src/git.ts`，离线的本地检查看不到它。Continuum
这一侧待跑：`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case command-injection-exec`
之后写入。与 `command-injection-exec-fixed` 成对，修好版用于测误报率。

## 证据

`bun replay/run.ts` 离线复验：对 `src/git.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "命令注入（child_process.exec 拼接）",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "pair": "command-injection-exec-fixed",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/",
    "https://www.wiz.io/blog/red-agent-snowflake-copilot-cicd-bug"
  ],
  "files": [
    "src/git.ts"
  ]
}
```
