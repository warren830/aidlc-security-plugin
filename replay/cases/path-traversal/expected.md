# 路径穿越（fs.readFile + path.join）

## 场景

`src/reports.ts` 的 `downloadReport` 把用户传入的 `name` 用 `path.join(REPORTS_DIR, name)` 拼起来
直接读文件。`join` 会把 `..` 段当成普通路径段折叠，所以 `name = "../../etc/passwd"` 会跳出
`/srv/app/reports` 读任意文件。OWASP A01（失效的访问控制）和 CWE-22 都覆盖这一类。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

待补。插件和 core 没有 security 类 sensor 覆盖 `src/reports.ts`，离线的本地检查看不到它。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case path-traversal` 之后写入。
与 `path-traversal-fixed` 成对，修好版用于测误报率。

## 证据

`bun replay/run.ts` 离线复验：对 `src/reports.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

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
