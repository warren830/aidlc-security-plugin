# 威胁模型漏了 STRIDE 章节

## 场景

Security Threat Model 的 Step 6 要求 `security-threat-model.md` 按顺序写 12 个 `##` 章节，STRIDE 六类各占
一节。某一类没有威胁时，这一节也要写一行，说明 review 在这一类没有发现威胁。这份威胁模型漏了
`## Repudiation`：抵赖类没有威胁，agent 就没写这一节。审批的人从文件里看不出这一类有没有检查过。

## 理论上应该在哪个环节被检测

威胁建模。core 的 `required-sections` 检查在 Security Threat Model 的门禁上按插件的模板
`security/tools/data/templates/security-threat-model.md` 检查 `##` 标题，缺哪一节就报哪一节。

## 现在的实现能否检测到

必备章节检查拦下，报出缺 `## Repudiation`。这个检查是 advisory：真实流程里，Step 7 的 report 先把缺的章节
交回 agent 补上，门禁上再报一次还缺的章节，由人决定，门禁不会因此关上。

`security-threat-model.md` 是 `uncovered-threat-fixed` 的威胁模型删掉 `## Repudiation` 一节，同样是手写的，
没有跑过真实的 AWS Security Agent 威胁模型 review。`repo/`、`security-scan-result.md`、`threat-coverage.json`
和 `.aidlc-security.json` 原样复制自 `uncovered-threat-fixed`，所以 Continuum 只报了一条 LOW，威胁覆盖检查
放行，只有必备章节检查拦下。这个用例不成对：`uncovered-threat-fixed` 的威胁模型 12 节齐全，它在报告里放行，
就是对照。

## 证据

`bun replay/run.ts --check` 像对 `uncovered-threat-fixed` 一样判 `security-scan-result.md` 和威胁覆盖，再在
用例目录下运行 core 的 `required-sections` worker，参数是 `--stage security-threat-model`、
`--template-eligible security-threat-model`，`--framework-templates-dir` 指向插件的模板目录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "威胁模型漏了 STRIDE 章节",
  "stage": "threat-model",
  "expected": "sections",
  "sources": [
    "https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html",
    "https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats"
  ],
  "files": [
    "src/jwt.ts"
  ]
}
```
