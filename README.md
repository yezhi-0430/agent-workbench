# Agent Workbench

基于 Python 标准库、SQLite 和 OpenRouter 的最小 Agent。主循环、工具注册及 session 管理自行实现，没有使用 Agent 框架。

## 启动

要求 Python 3.10+，无需安装依赖。PowerShell：

```powershell
$env:OPENROUTER_API_KEY = '你的密钥'
$env:OPENROUTER_MODEL = 'openai/gpt-4o-mini'
python server.py
```

打开 http://127.0.0.1:8765 。模型须支持工具调用；实际费用和可用性取决于 OpenRouter 账户。不要提交密钥。数据库 `agent.db` 保存在当前目录。

运行测试：`python -m unittest discover -s tests -v`。

## 设计

浏览器通过 HTTP 使用 session API，聊天接口逐行推送 JSON 事件；每个 session 同时只允许一个运行。模型调用 OpenRouter 的 Chat Completions 接口，运行时解析工具调用、执行并把结果放回消息，直到得到答案或达到 8 轮上限。计算器用 AST 白名单解析，搜索是明确标注的 mock，todo 通过 SQLite 按 session 隔离。停止在当前阻塞模型请求返回后生效，网络请求超时 60 秒。

## Memory 与 context

消息和工具结果按 session 持久化；每次请求载入当前 session。运行时在超过 8 个用户轮次或近期消息超过约 22000 字符时压缩较早的完整轮次（字符数只是上下文大小的粗略估计，并不保证匹配任何模型的 token 窗口）。较早内容分片与已有摘要合并，全部成功后才保存摘要及覆盖位置；压缩失败会停止本次请求，保留原始历史并提示重试。超长单轮无法安全压缩时提示用户缩短输入或工具结果。摘要有损，可能遗漏或误记，并产生额外模型调用和费用。待办的权威状态在 SQLite 中，用户询问时由模型调用 todo 读取。无跨 session 召回或长期用户画像。模型不一定提供思维链，因此 trace 不依赖内部推理。

## 限制

这是仅绑定 localhost 的演示应用，无登录或多用户授权；不要暴露到公网。工具结果和对话存储在本地明文数据库。停止不立即中断正在进行的 HTTP 请求。搜索不是实时搜索。

## 网络错误处理

对连接异常、超时及 HTTP 429/500/502/503/504 最多重试两次；认证等其他 HTTP 错误不会重试。普通对话记忆与待办任务通过系统提示和工具描述区分，模型仍可能偶尔误判。

停止请求会在当前模型请求返回后检查；如果一组工具中还有未执行项，运行时记录取消结果，保持后续请求所需的工具调用与结果配对。当前模型请求本身不能立即中断。

工具通过 `Registry.register(schema, handler)` 注册，运行循环按名称分发；当前校验覆盖必填字段、额外字段、基本类型和枚举，并非完整 JSON Schema 实现。

## 演示路径

1. 新建会话，输入“我叫小林”，然后问“我叫什么？”；观察普通记忆不会创建待办。
2. 输入“添加待办：准备周报”，展开右侧 todo 卡片查看参数、结果和耗时。
3. 新建另一个会话，输入“列出我的待办”，验证为空；切回第一个会话继续追问。
4. 连续对话超过 8 个用户轮次，观察执行记录中的上下文压缩卡片，再追问较早的事实。摘要有损，结果须实际核对。

执行记录在运行时展示模型名称、成功请求的耗时与重试次数，以及工具调用状态和耗时；模型、工具、压缩和错误事件按会话保存，切换会话后恢复；旧会话没有新格式记录时从消息历史恢复工具记录。断线清理通过本地真实 TCP 断开测试，测试中的 Agent 使用可控替身。

进程在工具调用与结果之间退出时，下次请求会在发送给模型的历史中补充“执行结果未知”，不会自动重跑工具。原始记录不被改写；如果工具有副作用，应检查实际状态后再决定是否重试。

## 需求与验证对应

| 需求 | 自动化验证 | 真实服务验证 |
| --- | --- | --- |
| 工具注册、参数校验和循环上限 | `test_registry.py`、`test_agent.py` | OpenRouter 计算器调用 |
| Session 持久化、隔离和并发 | `test_persistence.py`、`test_concurrency.py` | 两会话待办隔离 |
| 对话追问与上下文压缩 | `test_persistence.py`、`test_summary.py`、`test_context_budget.py`、`test_tool_budget.py` | 构造长历史后召回早期代号；单次验证 |
| 停止、断线和中断历史恢复 | `test_cancellation.py`、`test_disconnect.py`、`test_http_disconnect.py`、`test_recovery.py`、`test_crash_integration.py` | HTTP 断线及强制进程退出测试使用可控模型替身；尚未用真实模型做强制崩溃测试 |
| Trace、重试与运行分组 | `test_resilience.py`、`test_trace_storage.py`、`test_trace_http.py`、`test_run_trace.py` | OpenRouter 模型和计算器事件 |

执行记录通过 `run_id`、UTC 时间、开始与结束事件区分各次运行；浏览器显示运行分隔。事件包含用户输入推导出的工具参数和结果，以明文保存在本地，请勿提交数据库。

项目结构：`agent.py` 负责模型接入、上下文和运行循环，`storage.py` 负责 SQLite，`tools.py` 负责工具和注册，`server.py` 负责 HTTP 与执行事件，`static/` 是浏览器界面。

每次模型请求之前也会检查消息总字符数；单轮内的工具结果导致超出预算时，停止运行并提示缩小查询，后续可继续对话触发旧轮次压缩。字符预算不包含完整工具 Schema、协议开销或供应商 token 计算，不构成模型窗口的硬保证。

待办参数按操作校验：`add` 只接受非空 `text`，`list` 不接受额外参数，`complete` 需要正整数 `id`。摘要内容超出保存上限时会停止当前请求，不会静默截断摘要或推进覆盖位置。
