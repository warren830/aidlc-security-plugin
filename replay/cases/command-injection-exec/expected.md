# 命令注入（child_process.exec 拼接）

## 场景

`src/git.ts` 的 `checkoutBranch` 用 `exec` 跑 `git checkout ${branch}`。`exec` 把整条字符串交给 shell 解析，
`branch` 里的 `;`、`&&`、反引号或 `$()` 都会被求值，等价于让远端输入直接进 shell。这是 OWASP A03
注入里最常见的一类。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `src/git.ts`，离线的本地检查看不到它。与 `command-injection-exec-fixed` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-5c8d27e8-289a-4d68-9e44-664f1a8aef00`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-90b44628-cd56-4571-b9d9-b6c77a33bea2`：HIGH，COMMAND_INJECTION: checkoutBranch() interpolates untrusted branch name into child_process.exec shell command, enabling arbitrary command execution，位置 `src/git.ts:6`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/git.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

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
