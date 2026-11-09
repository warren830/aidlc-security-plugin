# 引用未固定 SHA 的 Action

## 场景

workflow 用 tag 引用第三方 Action（`actions/checkout@v4`、`tj-actions/changed-files@v45`）。
tag 可以在评审之后被改指向别的代码。出处是 tj-actions/changed-files 和 Trivy 两次 tag 被改的事件。
`repo/.github/workflows/build.yml` 是最小样本，唯一的 `run` 只 echo 一个标记。

## 理论上应该在哪个环节被检测

CI：PR 引入或修改 workflow 时，检查每个 `uses:` 是否固定到完整的 commit SHA。
AI-DLC 生成这个文件时，代码生成门禁也可能拦下，但 diff scan 是否会报这一类不确定，所以这里不算。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `.github/workflows/build.yml`，离线的本地检查看不到它。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的
AWS Continuum 差分 code review（job `cj-25a2a2cb-cebe-419c-b04a-4bb04880409c`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-d9545f10-915d-45fa-b760-96831d979447`：HIGH，OTHER: CI workflow uses known-compromised tj-actions/changed-files@v45 pinned to mutable tag (CVE-2025-30066)，位置 `.github/workflows/build.yml:14`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `.github/workflows/build.yml` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "引用未固定 SHA 的 Action",
  "stage": "ci",
  "expected": "continuum",
  "sources": [
    "https://www.stepsecurity.io/blog/harden-runner-detection-tj-actions-changed-files-action-is-compromised",
    "https://www.wiz.io/blog/trivy-compromised-teampcp-supply-chain-attack"
  ],
  "files": [
    ".github/workflows/build.yml"
  ]
}
```
