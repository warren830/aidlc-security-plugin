# 验证测试套件

每个用例是一个最小场景，记录它理论上应该在哪个环节被检测，以及这个仓库现在的实现能否检测到。
`bun replay/run.ts` 离线跑完所有用例，生成 [`REPORT.md`](REPORT.md)。

## 一个用例

`cases/<id>/` 下有：

- `repo/`：场景的最小仓库。runner 只读里面的文件，从不执行，内容都是无害的占位。
- `security-scan-result.md`（可选）：录制的 AWS Security Agent 扫描记录，格式和 Code Generation
  Step 4b 写的一样，用来演示门禁这一侧。
- `expected.md`：场景、理论检测环节、现在能否检测到、证据，以及唯一一个 `json` 块：

| 字段 | 值 |
| --- | --- |
| `vector` | 报告里的测试向量名 |
| `stage` | `threat-model`、`code-generation-gate` 或 `ci` |
| `expected` | `detected`、`not-detected` 或 `needs-aws` |
| `sources` | 场景的公开出处 URL |
| `files` | `repo/` 下承载场景的文件，相对 `repo/` |
| `record` | 录制样本的文件名，没有就不写 |
| `gap_owner` | `expected` 是 `not-detected` 时必填：`plugin` 或 `action`（AWS-9） |
| `aws_run` | 可选。对真实 AWS Security Agent 跑过的结果：`result`（`detected` 或 `not-detected`）、`at`、`region`、`code_review_job_id`、`findings`。CI 不重跑它，它也不改变 `expected` |

## 结果怎么算

runner 对每个用例做两件事：

1. 对 `files` 里的每个文件，找出 core 和插件里 `category: security`、`matches` 覆盖它的
   sensor，逐个运行。有一个不通过，结果就是 `detected`。
2. 有 `record` 时，对它运行 `security-findings-gate`。门禁拦下，结果是 `needs-aws`：门禁这一侧有效，
   但扫描本身要调用 Security Agent。

两步都没检测到，结果就是 `not-detected`。

`expected` 只描述离线能测出的结果，所以要调用 Security Agent 的用例在 CI 里永远是
`needs-aws`。真实扫描跑过以后，结果写进 `aws_run`，报告里单列「AWS 实测」一栏。

结果和 `expected` 不一致时，`run.ts` 失败。缺口不能靠改报告藏起来；补上缺口以后，
也要同时改 `expected.md`。

## 运行

```bash
bun replay/run.ts           # 重新生成 REPORT.md
bun replay/run.ts --check   # CI 用：结果和预期不一致，或者 REPORT.md 过期，就失败
```

runner 读 aidlc-workflows checkout 里的 core sensor，所以和 `bun run test` 一样需要
`AIDLC_WORKFLOWS_DIR`（见仓库根目录的 README）。

看起来像凭证的样本用明显是假的值，并且在仓库根目录的 `.gitleaks.toml` 里放行。
