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

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `.github/workflows/triage.yml`，离线的本地检查看不到它。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的
AWS Continuum 差分 code review（job `cj-111aceb1-326e-472f-87f2-0d410f7a6b7d`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-0681b67b-b2fb-498f-8a06-f520a93c261c`：HIGH，PRIVILEGE_ESCALATION: "Pwn request": pull_request_target workflow checks out untrusted PR head with contents:write token，位置 `.github/workflows/triage.yml:16`。
- `f-61cfe730-2786-47d2-9238-62716fae2176`：CRITICAL，COMMAND_INJECTION: GitHub Actions script injection: issue title interpolated into run: shell in privileged workflow，位置 `.github/workflows/triage.yml:19`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `.github/workflows/triage.yml` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "pull_request_target 和 issue 标题注入",
  "stage": "ci",
  "expected": "continuum",
  "sources": [
    "https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation",
    "https://www.wiz.io/blog/red-agent-snowflake-copilot-cicd-bug",
    "https://www.stepsecurity.io/blog/mini-shai-hulud-is-back-a-self-spreading-supply-chain-attack-hits-the-npm-ecosystem"
  ],
  "files": [
    ".github/workflows/triage.yml"
  ]
}
```
