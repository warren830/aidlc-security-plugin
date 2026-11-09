# 路径穿越 — 修好版

## 场景

和 `path-traversal` 是同一处的修复：用 `path.resolve` 把 `REPORTS_DIR` 和 `name` 折叠成绝对路径，
再检查解析结果仍以 `REPORTS_DIR + sep` 开头。任何 `..` 段解析后跳出根目录的输入都会被拒绝。
这是 `path-traversal` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的路径穿越 finding。

## 现在的实现能否检测到

待补。本用例与 `path-traversal` 成对，预期结果是 `not-detected`。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case path-traversal-fixed` 之后写入。

## 证据

`bun replay/run.ts` 离线复验：对 `src/reports.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "路径穿越 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "path-traversal",
  "gap_owner": "plugin",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/reports.ts"
  ]
}
```
