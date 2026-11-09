# 路径穿越（fs.readFile + path.join）

## 场景

`src/reports.ts` 的 `downloadReport` 把用户传入的 `name` 用 `path.join(REPORTS_DIR, name)` 拼起来
直接读文件。`join` 会把 `..` 段当成普通路径段折叠，所以 `name = "../../etc/passwd"` 会跳出
`/srv/app/reports` 读任意文件。OWASP A01（失效的访问控制）和 CWE-22 都覆盖这一类。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `src/reports.ts`，离线的本地检查看不到它。与 `path-traversal-fixed` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-5c195f54-5cf7-4419-aa87-8887957753ac`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-0bab57b9-623f-45ed-ac94-d0f07457c0ba`：HIGH，PATH_TRAVERSAL: downloadReport joins user-supplied filename into REPORTS_DIR without containment check (arbitrary file read)，位置 `src/reports.ts:9`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/reports.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "路径穿越（fs.readFile + path.join）",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "pair": "path-traversal-fixed",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/"
  ],
  "files": [
    "src/reports.ts"
  ]
}
```
