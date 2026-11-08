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

未检测到。插件和 core 都没有 sensor 覆盖 `.claude/settings.json`、`.mcp.json` 或 `.vscode/tasks.json`。
插件的组件都在 AI-DLC 会话里运行，结构上就拦不住打开仓库时执行的命令。建议由 AWS-9 的 Action 补：在 PR 上
标出这类文件的新增和改动。

## 证据

`bun replay/run.ts --check` 对 `files` 里的每个文件跑了所有覆盖它的 security 类 sensor。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "打开仓库就执行的 agent 配置",
  "stage": "ci",
  "expected": "not-detected",
  "sources": [
    "https://www.stepsecurity.io/blog/miasma-worm-hits-microsoft-again-azure-functions-action-and-72-other-repositories-disabled-after-supply-chain-attack-targeting-ai-coding-agents",
    "https://www.stepsecurity.io/blog/tensorlake-npm-compromised-hostage-token-worm",
    "https://www.wiz.io/blog/amazon-q-vulnerability"
  ],
  "files": [
    ".claude/settings.json",
    ".mcp.json",
    ".vscode/tasks.json"
  ],
  "gap_owner": "action"
}
```
