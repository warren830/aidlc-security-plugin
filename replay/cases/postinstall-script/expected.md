# 依赖的 postinstall 脚本

## 场景

项目依赖的 `example-helper` 声明了 `postinstall`，`npm install` 时会自动执行。Nx s1ngularity 的恶意版本
就是在这一步调用本机的 AI CLI 去找凭证，cline@2.3.0 在这一步偷偷装了别的软件。这里的 `postinstall.js`
是无害占位，只在当前目录写一个 `replay-marker.txt`，不调用任何 CLI，不读任何文件，也不联网。

## 理论上应该在哪个环节被检测

CI：PR 新增依赖，或者依赖的新版本带安装脚本时，标出来让人审查。AI-DLC 加这个依赖时，代码生成门禁的
diff scan 能看到 `package.json` 的改动，但看不到发布到 registry 的包里有什么，所以不算。

## 现在的实现能否检测到

未检测到。插件和 core 都没有 sensor 覆盖 `package.json` 或依赖里的脚本，插件也不检查安装脚本。
建议由 AWS-9 的 Action 补：在 PR 上比较依赖的变化，标出带 install 脚本的包。

## 证据

`bun replay/run.ts --check` 对 `files` 里的每个文件跑了所有覆盖它的 security 类 sensor。实际结果和下面的
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
