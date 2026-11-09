# 依赖的 postinstall 脚本

## 场景

项目依赖的 `example-helper` 声明了 `postinstall`，`npm install` 时会自动执行。Nx s1ngularity 的恶意版本
就是在这一步调用本机的 AI CLI 去找凭证，cline@2.3.0 在这一步偷偷装了别的软件。这里的 `postinstall.js`
是无害占位，只在当前目录写一个 `replay-marker.txt`，不调用任何 CLI，不读任何文件，也不联网。

## 理论上应该在哪个环节被检测

CI：PR 新增依赖，或者依赖的新版本带安装脚本时，标出来让人审查。AI-DLC 加这个依赖时，代码生成门禁的
diff scan 能看到 `package.json` 的改动，但看不到发布到 registry 的包里有什么，所以不算。

## 现在的实现能否检测到

未检测到。Continuum 报出了这个问题，但等级低于门禁的 HIGH 阈值，插件门禁放行。插件和 core 没有 security 类 sensor 覆盖 `package.json`、`vendor/example-helper/package.json`、`vendor/example-helper/postinstall.js`，离线的本地检查看不到它。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的
AWS Continuum 差分 code review（job `cj-d4673b60-ee67-480c-b64d-84f0fe524893`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-9ad052a9-6f47-44ee-9185-5bdbf5db5210`：MEDIUM，CODE_INJECTION: Vendored dependency adds npm postinstall hook, executing repo-controlled code on every install (CI/dev)，位置 `vendor/example-helper/package.json:4`。

这项缺口建议由 AWS-9 的 Action 补：在 PR 上对新增或改动的 install 脚本做确定性检查，不依赖 Continuum 给出的等级。
插件也可以在门禁里把这类 finding 单独按阻塞处理，但阈值是插件统一的设置，改它会影响所有用例。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `package.json`、`vendor/example-helper/package.json`、`vendor/example-helper/postinstall.js` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "依赖的 postinstall 脚本",
  "stage": "ci",
  "expected": "not-detected",
  "sources": [
    "https://www.stepsecurity.io/blog/supply-chain-security-alert-popular-nx-build-system-package-compromised-with-data-stealing-malware",
    "https://www.stepsecurity.io/blog/cline-supply-chain-attack-detected-cline-2-3-0-silently-installs-openclaw"
  ],
  "files": [
    "package.json",
    "vendor/example-helper/package.json",
    "vendor/example-helper/postinstall.js"
  ],
  "gap_owner": "action"
}
```
