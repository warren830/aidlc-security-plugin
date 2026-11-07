# 引用未固定 SHA 的 Action

## 场景

workflow 用 tag 引用第三方 Action（`actions/checkout@v4`、`tj-actions/changed-files@v45`）。
tag 可以在评审之后被改指向别的代码。出处是 tj-actions/changed-files 和 Trivy 两次 tag 被改的事件。
`repo/.github/workflows/build.yml` 是最小样本，唯一的 `run` 只 echo 一个标记。

## 理论上应该在哪个环节被检测

CI：PR 引入或修改 workflow 时，检查每个 `uses:` 是否固定到完整的 commit SHA。
AI-DLC 生成这个文件时，代码生成门禁也可能拦下，但 diff scan 是否会报这一类不确定，所以这里不算。

## 现在的实现能否检测到

未检测到。插件没有 sensor 覆盖 `.github/workflows/`，`aidlc-security-action` 的 main 上还没有任何检查。
AWS-9 的 PR（warren830/aidlc-security-action#1，未合并）里有 `action-pinning` 检查。
这项缺口建议由 AWS-9 的 Action 补：它在 PR 上运行，能看到不经过 AI-DLC 的 workflow 改动。

## 证据

`bun replay/run.ts --check` 对 `repo/.github/workflows/build.yml` 跑了所有覆盖它的 security
类 sensor。实际结果和下面的 `expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "引用未固定 SHA 的 Action",
  "stage": "ci",
  "expected": "not-detected",
  "sources": [
    "https://www.stepsecurity.io/blog/harden-runner-detection-tj-actions-changed-files-action-is-compromised",
    "https://www.wiz.io/blog/trivy-compromised-teampcp-supply-chain-attack"
  ],
  "files": [".github/workflows/build.yml"],
  "gap_owner": "action"
}
```
