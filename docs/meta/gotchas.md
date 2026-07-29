# Gotchas & Design Principles

> 从 paper-qa 2026-07 系列 debug 中抽象出来。每条都是"踩过"的真实经验。
> 遇到新问题时，先想"这条怎么用"，再下手。
>
> **维护方式**：每次踩坑，在对应原则下追加；不要按日期，用原则类型组织。

---

## G1: 异步与生命周期

### 不要用 BackgroundTasks 跑 async 协程

任务脱离任何事件循环，永远不会被 await。解法：要么全 sync，要么全 async，要么用 `asyncio.run_coroutine_threadsafe` 显式跨边界。

### 跨边界用正确的桥接方式

`anyio.to_thread.run_sync(async_fn)` 是错的，async 函数需要在事件循环中运行。在前端 component 里启动全局任务也是错的——进程死了谁回收？

---

## G2: 流式/订阅系统

### SSE 订阅前事件必须缓冲，订阅时 flush

否则订阅前的事件永远丢失，前端显示"卡在第一步"。解法：订阅时先查历史，flush 后再开始接收新事件。

### 订阅必须收到终止信号才能 return

没有 DONE / ERROR / CLOSE，consumer 会永远等下一个事件。

### 订阅不存在的资源立即报错，不要无限等

先查 → 不存在 → 发 ERROR + DONE 退出。

### 测试 async stub 要 `await asyncio.sleep(0)`

纯同步 stub 让协程永远不让出控制，导致死锁。

---

## G3: 跨边界数据契约

### 谁改字段谁负责同步所有层

后端是权威源 → 前端 normalizer 跟着改，不要反过来。

### snake_case / camelCase 不要混用

Python/JSON 用 snake，TS 用 normalizer 转 camel。选一种就贯彻到底。

### schema 变更要先讨论影响面

加字段 / 改类型 / 删除字段，会让前端、测试、缓存全部要改。

### 响应信封结构不要随意压平

嵌套结构是为消费方服务的，压平后前端拿不到完整数据。

---

## G4: 异常必须可观测

### 每个 catch 块至少一个可观测副作用

- **差**：`except: pass` —— bug 永远找不到
- **中**：`except: logger.error(e); continue` —— 调试慢，但能找到
- **好**：`except: emit_event(...) / set state field / return error response` —— 用户能看到，测试能验

如果只能 log，就升级到 emit state 或 event。

---

## G5: 前端 UI 渲染

### 单个组件崩溃会污染整个组件树

Vue/React 中一个组件渲染异常会让 router-view 失效，看起来像"导航坏了"。

### 所有外部数据按 optional 处理

`x?.foo` 而不是 `x.foo`，类型也标记 `T | undefined`。后端/Pydantic 过来的数据都在信任边界外。

### HMR 不更新直接重启 dev server

不要花时间排查 HMR，重启是最快的解法。

---

## G6: 基础类型与常量

### datetime 永远显式带 tz

`datetime.now(UTC)` 而不是 `datetime.utcnow()`，混合比较直接 `TypeError`。

### 布尔反向参数要写测试

`reverse=True` 表示"最新的在前"，不测就会搞反。

### None / 空字符串 / 0 / [] / {} 不混用

在边界统一 "missing" 的语义。

---

## G7: Git 操作

### `git revert <commit>` 会物理删除文件

不只是从历史移除，是真的删文件。恢复：`git show <commit>:<path> > <path>`

### `.gitignore` 目录不要 `git add -f`

ignore 是有原因的；改之前先问"为什么被 ignore 了？"

### `git push --force` 慎用

用 `--force-with-lease` 或先确认没有别人已 pull。

### `git reset --hard` 之前先 `git stash`

除非确认 dirty 为空。

### 提交前确认 dirty files 范围

避免把"上一个 session 的遗留"混进新 commit。原则：改任何东西前先 `git status` 看 dirty。

---

## G8: 工作区状态

### cwd 是最容易被忽略的变量

看到 `git status` 输出异常（untracked 里有 `../.aws`），**第一怀疑是 cwd 错了**，不是仓库状态。

### 跨项目操作用绝对路径

不要假设当前目录。

### 同名文件的权威路径要唯一

操作前用 `glob` 确认。

---

## G9: 调试方法论

### 先列最简假设，最小实验排除

不要被表象带跑。高级 bug 的根因往往极简单。

### 实测反直觉对照表

| 现象 | 直觉以为是 | 实际经常是 |
|------|-----------|-----------|
| `getattr(x, '_attr', None)` 永远 None | 元数据丢了 | 这个属性从来没人设过 |
| 后端接口返回 None | 持久化失败 | 读的是错的实例 / 错的字段 |
| 前端 `.toFixed()` 崩 | 数据计算错 | 字段名拼错 / 后端就没返回 |
| SSE 卡死 | 网络/库 bug | 订阅前事件丢了 / 没终止信号 |
| `git status` 输出奇怪 | 仓库坏了 | cwd 漂移到别的目录了 |
| Vite HMR 不更新 | 缓存问题 | 重启 dev server |
| 设置保存不生效 | 数据库写失败 | 前端字段名 ≠ 后端 schema 字段名 |
| 测试断言失败 | 逻辑反了 | 断言本身写反（reverse / contains / not contains） |
| 导入模块失败 | 版本不兼容 | 循环导入 / cwd 错了 |
| LLM 输出乱码 | 模型坏了 | token 上限 / 多轮上下文截断 |

---

## G10: 决策与约束

### "加列 / 改 schema / 重构" 类决策先问清楚

影响哪些下游？前后端要协调吗？

### 用户前后要求矛盾立刻收手

不要先做再撤销，立刻问澄清。

### "看似无害"的临时改动都要立即处理

disable lint / catch 异常 / 注释掉测试——都要立即删掉或记录原因，不要留 TODO。

---

## 实际踩坑记录

### 删除启发式兜底后 _TrackedLLMAdapter 测试桩全部失败

**触发条件**：删除了 `analyze_and_expand_query` 中的 `try/except` 兜底，改为直接抛错
**现象**：11 个 engine 测试同时失败，`session.stop_reason == ERROR` 而非预期的 `NO_NEW_PAPERS`
**根因**：`_TrackedLLMAdapter` 只暴露 `call_single`，不暴露 `acomplete`；`FakeLLM.call_single` 原本返回 `answer_payload`（非 JSON），query understanding 阶段触发 `_extract_json` 抛 `ValueError` → 旧代码走 `_heuristic_understanding` 兜底成功返回合法 QU → 新代码直接抛错被 `engine.arun` 的 `except Exception` 捕获 → `stop_reason = ERROR`
**解法**：修改 `FakeLLM.call_single` 在首次调用时返回 JSON payload（query 阶段），后续返回 `answer_payload`（answer 阶段）；同样修复 `FailingAnswerLLM.call_single` 首次返回 JSON 避免误拦截 query 阶段

### git status --short 列显示顺序导致误判 dirty files

**触发条件**：commit 前用 `git status` 查看 dirty 状态
**现象**：文件显示在"中间列"（`M  path`），误以为未 staged
**根因**：git porcelain 格式：`第二列`=工作区，第一列`M` = index staged；`M `（第一列有 M）= staged 且 dirty，` M`（第二列有 M）= 仅工作区 dirty。本项目多数文件都是 ` M`（仅工作区），但 index.ts/tsconfig 因为之前 session 已经 `git add` 过所以是 `M `（staged），被混入了本应另开的 commit
**解法**：commit 前用 `git diff --staged --stat` 确认 staged 内容；发现无关文件在 staged 区，用 `git reset HEAD~1 -- path` 移出后 `git checkout HEAD~1 -- path` 恢复工作区

---

## 一句话总结

> **异步先想所有权与生命周期，流式先想起点+终点+缓冲，契约先想权威源+类型先行，异常先想是否可观测，组件先想是否污染全局，git 先想是否会物理改文件，调试先想最简单的解释。**
