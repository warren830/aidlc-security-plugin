# 打开仓库就执行的 agent 配置

## 场景

仓库里提交了 agent 和编辑器的项目配置，打开仓库就会跑命令：`.claude/settings.json` 的 SessionStart hook、
`.mcp.json` 里的 MCP 服务器、`.vscode/tasks.json` 里 `runOn: folderOpen` 的任务。Miasma 蠕虫靠植入这类文件
传播，tensorlake 恶意包写入 `.claude/settings.json` 和 `.vscode/tasks.json` 来持久化，Amazon Q、Claude Code、
Cursor 都出过自动加载工作区 MCP 配置的 CVE。这里每条命令都只 echo 一个标记，或者往本地 `replay-marker.txt` 追加一行。

## 理论上应该在哪个环节被检测

CI：PR 新增或修改这些会自动执行的配置时，要求人明确审查。命令在打开仓库的那一刻就跑了，比 AI-DLC 的任何
阶段都早，所以威胁建模和代码生成门禁都来不及拦。运行时的防线是 harness 自己的信任确认，不在本仓库范围内。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `.claude/settings.json`、`.mcp.json`、`.vscode/tasks.json`，离线的本地检查看不到它。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的
AWS Continuum 差分 code review（job `cj-57dee867-17e2-4bb2-b2bc-4bb4b7088a65`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-409b902c-ae0a-4ab8-8b3e-49ec0c26d0c6`：HIGH，CODE_INJECTION: VS Code task with runOn:folderOpen auto-executes committed shell command on opening repo，位置 `.vscode/tasks.json:1`。
- `f-8053e941-2b9f-4948-bdfa-ad292f62b630`：HIGH，CODE_INJECTION: Committed autorun developer-tool configs (VS Code folderOpen task, Claude SessionStart hook) execute repo-controlled shell commands without consent，位置 `.vscode/tasks.json:1`。
- `f-cfa41421-10f1-4abd-bf85-36d614bb5898`：MEDIUM，CODE_INJECTION: Committed project-scoped .mcp.json auto-launches a repo-defined subprocess on the developer machine，位置 `.mcp.json:1`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `.claude/settings.json`、`.mcp.json`、`.vscode/tasks.json` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "打开仓库就执行的 agent 配置",
  "stage": "ci",
  "expected": "continuum",
  "sources": [
    "https://www.stepsecurity.io/blog/miasma-worm-hits-microsoft-again-azure-functions-action-and-72-other-repositories-disabled-after-supply-chain-attack-targeting-ai-coding-agents",
    "https://www.stepsecurity.io/blog/tensorlake-npm-compromised-hostage-token-worm",
    "https://www.wiz.io/blog/amazon-q-vulnerability"
  ],
  "files": [
    ".claude/settings.json",
    ".mcp.json",
    ".vscode/tasks.json"
  ]
}
```
