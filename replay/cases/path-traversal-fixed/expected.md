# 路径穿越 — 修好版

## 场景

和 `path-traversal` 是同一处的修复：用 `path.resolve` 把 `REPORTS_DIR` 和 `name` 折叠成绝对路径，
再检查解析结果仍以 `REPORTS_DIR + sep` 开头。任何 `..` 段解析后跳出根目录的输入都会被拒绝。
这是 `path-traversal` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的路径穿越 finding。

## 现在的实现能否检测到

放行，符合预期。Continuum 没有报出 HIGH 及以上的 finding，插件门禁不拦。插件和 core 没有 security 类 sensor 覆盖 `src/reports.ts`，离线的本地检查看不到它。与 `path-traversal` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-ab6cb970-bc91-4b76-b4f8-982598dd2e04`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它没有报出任何 finding。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/reports.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "路径穿越 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "path-traversal",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/reports.ts"
  ]
}
```
