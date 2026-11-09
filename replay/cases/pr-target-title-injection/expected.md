# pull_request_target 和 issue 标题注入

## 场景

workflow 用 `pull_request_target` 触发，带着可写的 token checkout 了 PR 的 head 再运行它；另一步把
`github.event.issue.title` 直接展开进 `run` 脚本，标题就成了脚本的一部分。hackerbot-claw 靠这两种写法
在多个仓库拿到了执行权限，Wiz 的 Red Agent 用构造的 issue 标题进入了 Snowflake，TanStack 那次也从
`pull_request_target` 起步。`repo/.github/workflows/triage.yml` 是最小样本，每个 `run` 只 echo。
checkout 已经固定到 SHA，这个用例只演示触发方式和注入，不和未固定 SHA 的用例重复。

## 理论上应该在哪个环节被检测

CI：PR 新增或修改 workflow 时，检查 `pull_request_target` 加 head checkout 的组合，以及 `run` 里直接
展开的 `github.event.*` 字段。AI-DLC 生成这个文件时，diff scan 也可能报出来，但这一点没有实测过，所以不算。

## 现在的实现能否检测到

未检测到。插件和 core 都没有 sensor 覆盖 `.github/workflows/`。建议由 AWS-9 的 Action 补：workflow
改动大多不经过 AI-DLC，只有在 PR 上检查才都看得到。

## 证据

`bun replay/run.ts --check` 对 `files` 里的每个文件跑了所有覆盖它的 security 类 sensor。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "pull_request_target 和 issue 标题注入",
  "stage": "ci",
  "expected": "not-detected",
  "sources": [
    "https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation",
    "https://www.wiz.io/blog/red-agent-snowflake-copilot-cicd-bug",
    "https://www.stepsecurity.io/blog/mini-shai-hulud-is-back-a-self-spreading-supply-chain-attack-hits-the-npm-ecosystem"
  ],
  "files": [
    ".github/workflows/triage.yml"
  ],
  "gap_owner": "action"
}
```
