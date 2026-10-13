# MCP Reliability, Cancellation, and Flow Control · MCP 可靠性、取消与流控

> 请求 ID 只负责把一条消息关联起来。它既不能让副作用变得安全，也不能停住一个 worker，更保护不了流不被慢消费者拖垮。
>
> A request ID correlates a message. It does not make a side effect safe, stop a worker, or protect a stream from a slow consumer.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 13, Lessons 09 and 13
**Time:** ~120 minutes

## Learning Objectives · 学习目标

- 为 stdio 与 Streamable HTTP 各自实现正确的取消（cancellation）信号
- 解决完成与取消之间的竞态（race），且不在取消之后发送消息
- 把请求取消与持久化的 `tasks/cancel` 语义区分开
- 依据副作用与显式幂等键（idempotency key）构建重试决策
- 在保住最终响应的同时限制进度队列（progress queue）的容量
- 通过重连（reconnect）、重新拉取（refetch）与带抖动的退避（jittered backoff）恢复流

> Implement the correct cancellation signal for stdio and Streamable HTTP.
> Resolve completion and cancellation races without sending messages after cancellation.
> Separate request cancellation from durable `tasks/cancel` semantics.
> Build retry decisions from side effects and explicit idempotency keys.
> Bound progress queues while preserving final responses.
> Recover streams through reconnect, refetch, and jittered backoff.

## The Problem · 问题在哪

最顺畅的快乐路径（happy path）恰恰藏着分布式系统里最昂贵的 bug。

客户端调用一个工具。服务端开始干活。进度消息不断到达。一个代理缓冲了这条流。客户端等到超时，断开连接。服务端在一毫秒之后完成。客户端带着新的 JSON-RPC id 重试。这次变更执行了两遍。

每个组件在本地都表现得无可指摘，系统却在全局失败了。

MCP 定义了消息与传输层行为，但下面这些仍然归你的应用所有：

- 时间预算；
- 业务幂等性（idempotency）；
- 有界队列；
- 重试分类；
- 持久任务状态；
- 重连与重新拉取策略。

本课把这些决策做进一个确定性模拟器。没有 sleep、没有 socket、没有随机故障。你直接控制取消事件的先后顺序。一个同步线程测试迫使两个账本客户端争抢同一个幂等键。

> The happy path hides the most expensive distributed-systems bugs. ... Every component behaved locally. The system failed globally. ... This lesson builds those decisions into a deterministic simulator. There are no sleeps, sockets, or random failures. You control cancellation event order directly. One synchronized thread test forces two ledger clients to compete for the same idempotency key.

## Request Cancellation Is Transport-Specific · 请求取消因传输而异

意图在每个传输上都一样：客户端不再需要某个在途（in-flight）的结果。但线上信号不同。

### stdio · stdio

stdio 使用一条共享的双向通道。客户端发送一个通知（notification）：

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/cancelled",
  "params": {
    "requestId": 41,
    "reason": "User closed the operation"
  }
}
```

该通知是 fire-and-forget 的。服务端不会为它发出任何 JSON-RPC 响应。

服务端应当停止工作、释放资源，并且不为被取消的请求发送响应。当请求未知、已经完成、或无法被安全停止时，服务端可以忽略取消。

格式错误、未知、以及已完成的取消通知都会被忽略。把这些竞态变成新的错误只会制造更多竞态。

> stdio uses one shared bidirectional channel. A client sends a notification ... The notification is fire-and-forget. The server emits no JSON-RPC response to it. ... The server should stop work, free resources, and avoid sending a response for the cancelled request. ... Malformed, unknown, and already completed cancellation notifications are ignored. Turning those races into new errors would create more races.

### Streamable HTTP · Streamable HTTP

现代 Streamable HTTP 给每个请求独立的 HTTP 响应或 SSE 响应流。客户端通过关闭该请求的响应流来取消。

不要为普通 HTTP 请求 POST `notifications/cancelled`。关闭流就是取消信号。

一旦服务端观察到断连，它应当停止工作，并且不得再为该请求发送任何消息。

> Modern Streamable HTTP gives each request its own HTTP response or SSE response stream. The client cancels by closing that request's response stream. ... Do not POST `notifications/cancelled` for an ordinary HTTP request. Stream closure is the cancellation signal. ... Once the server observes the disconnect, it should stop work and must not send more messages for that request.

### Server-sent cancellation is narrow · 服务端发起的取消用途很窄

服务端不用 `notifications/cancelled` 去取消任意的客户端调用。在 stdio 上，服务端发起的取消只保留给终止 `subscriptions/listen` 请求这一种用途。把这条路径与普通的客户端请求取消分开维护。

> A server does not use `notifications/cancelled` to cancel arbitrary client calls. On stdio, server-sent cancellation is reserved for terminating a `subscriptions/listen` request. Keep that path separate from ordinary client-request cancellation.

## Cancellation Is a Race · 取消是一场竞态

两种事件顺序都合法。

### Cancellation wins · 取消获胜

```text
request starts
client sends cancellation signal
server marks request cancelled
worker reaches completion
server suppresses the response
```

### Completion wins · 完成获胜

```text
request starts
worker commits the result
server sends the response
cancellation arrives late
server ignores the late notification
```

客户端同样必须忽略它已经放弃的请求迟到的响应。网络延迟意味着任何一方都无法证明对方先观察到哪个事件。

```figure
mcp-reliability-race
```

本课的 `RequestCoordinator` 只保存一个终态。取消之后 `complete()` 不再返回响应。迟到的取消改变不了一条已完成的记录。

> Two event orders are both valid. ... The client must also ignore a late response for a request it already abandoned. Network latency means neither side can prove which event the other side observed first. ... The lesson's `RequestCoordinator` stores one terminal state. `complete()` returns no response after cancellation. A late cancellation cannot change a completed record.

## Timeouts Need Two Clocks · 超时需要两个时钟

单一的不活动计时器不够用。

使用两个上限：

1. **空闲超时（idle timeout）。** 请求可以多久不产生有效活动。
2. **最大超时（maximum timeout）。** 从请求开始算起的绝对墙钟预算。

进度可以重置空闲时钟。它绝不能移除最大截止时间。

```text
start: 0 ms
progress: 400 ms
progress: 800 ms
progress: 1200 ms
idle timeout: 500 ms
maximum timeout: 2000 ms
```

在 1500 ms 时，请求仍然活跃，因为最新进度只过去了 300 ms。在 2000 ms 时，即使 1999 ms 又来了一个进度事件，最大截止时间也会取消它。

进度是可选的。服务端可以接受进度令牌（progress token）而一个更新都不发。绝不要因为令牌存在就给出无限超时。

MCP 进度值必须递增。通知在完成或取消之后停止。对进度做限流，免得跑得太快的 worker 淹没传输层。

> A single inactivity timer is not enough.
> 1. **Idle timeout.** How long the request may produce no useful activity.
> 2. **Maximum timeout.** The absolute wall-clock budget from request start.
> Progress may reset the idle clock. It must never remove the maximum deadline.
> Progress is optional. A server can accept a progress token and emit no updates. Never turn the presence of a token into an infinite timeout.

## Request Cancellation Is Not `tasks/cancel` · 请求取消不是 `tasks/cancel`

这两个机制解决的是不同的生命周期。

| 机制 | 目标 | 信号 | 成功意味着什么 |
|-----------|--------|--------|--------------------|
| stdio 上的请求取消 | 一个在途 RPC | `notifications/cancelled` | 客户端放弃了请求；服务端在可行时应停止 |
| HTTP 上的请求取消 | 一个在途响应流 | 关闭流 | 客户端放弃了请求；服务端在可行时应停止 |
| `tasks/cancel` | 一个持久 Task | 普通 MCP 请求 | 服务端确认了取消意图 |

`tasks/cancel` 返回成功并不证明 worker 停下了。在 worker 检查点（checkpoint）观察到标志之前，任务可能仍是 `working`。工作也可能在检查点之前就完成。

HTTP 连接关闭时，不要抹掉持久任务状态。创建 Task 的理由正是：它的生命周期比一次请求、一条连接更长。

> These mechanisms solve different lifetimes. ... A successful `tasks/cancel` result does not prove the worker stopped. The task may remain `working` until a worker checkpoint observes the flag. Work may complete before that checkpoint. ... Do not erase durable task state when the HTTP connection closes. The reason to create a Task is that its lifecycle outlives one request and one connection.

## A New JSON-RPC ID Is Not Idempotency · 新的 JSON-RPC ID 不是幂等性

JSON-RPC id 用来关联请求与响应。它们不标识一个业务操作。

假设客户端用 id `41` 提交一笔扣款，弄丢了响应，然后用 id `42` 重试。服务端看到的是两条不同的消息。没有应用层键，它无法知道这两条消息代表同一次结算（checkout）。

幂等键（idempotency key）标识的是业务意图：

```json
{
  "name": "charge_account",
  "arguments": {
    "account": "acct-7",
    "cents": 1200,
    "idempotencyKey": "checkout-7"
  }
}
```

服务端存储：

- 这个键；
- 操作参数的指纹（fingerprint）；
- 已提交的结果。

相同的键加相同的参数 → 返回存储的结果。相同的键配不同的参数 → 拒绝。这防止意外的键复用去改动另一个业务操作。

> JSON-RPC ids correlate requests and responses. They do not identify a business operation. ... An idempotency key identifies the business intent ... The same key and same arguments return the stored result. The same key with different arguments is rejected. This prevents accidental key reuse from mutating a different business operation.

### The ledger boundary must be atomic and durable · 账本边界必须原子且持久

下面这个序列是不安全的：

```text
check key
run mutation
store result
```

两个 worker 可能都观察到键缺失，然后都执行变更。在副作用之后、存储之前崩溃，会在重试时制造同样的歧义。

本课使用一个基于文件的 SQLite 账本（ledger）。`BEGIN IMMEDIATE` 把键检查、模拟的业务副作用、执行计数器和存储的结果串成一个事务。因此，两个拿着相同键相互竞争的独立账本连接只会观察到一个已提交结果和一次执行。关闭再重新打开账本，记录仍在。

每个返回值都从存储的 JSON 重建。调用者永远拿不到账本持有的那个可变对象，所以改动一个返回的字典不会污染后续的重放结果。

模拟器的业务副作用就是同一个 SQLite 事务里的回执和执行计数器。真实的支付、部署或外部 API 调用并不会因为写了一张本地表就变原子。生产环境需要持久的共享数据库事务、事务性发件箱（transactional outbox），或者一个强制相同幂等键的上游提供方。单靠进程锁既保护不了多个副本，也熬不过一次重启。

> This sequence is unsafe ... Two workers can both observe a missing key and both run the mutation. A crash after the effect but before the store creates the same ambiguity on retry. ... The lesson uses a file-backed SQLite ledger. `BEGIN IMMEDIATE` serializes the key check, simulated business effect, execution counter, and stored result into one transaction. ... Every return value is reconstructed from stored JSON. ... A real payment, deployment, or external API call is not made atomic merely by writing a local table. Production needs a durable shared database transaction, a transactional outbox, or an upstream provider that enforces the same idempotency key. A process lock alone does not protect multiple replicas or survive a restart.

### Retry matrix · 重试矩阵

先分类，再实现重试。

| 类别 | 例子 | 重试规则 |
|------|---------|------------|
| 安全 | 无副作用的确定性读 | 在弄清故障边界之后，用新的 JSON-RPC id 重试 |
| 有条件 | 带持久幂等键的变更 | 用相同的键和完全相同的参数重试 |
| 不安全 | 没有业务去重的变更 | 不要自动重试；先对账（reconcile） |

`readOnlyHint`、`idempotentHint` 这类工具注解仍然只是不可信的提示。重试安全性由应用契约与服务端实现决定。

> Classify retries before implementing them. ... Tool annotations such as `readOnlyHint` and `idempotentHint` remain untrusted hints. The application contract and server implementation decide retry safety.

## Backpressure Is Part of Correctness · 背压是正确性的一部分

SSE 生产者生成进度的速度可能超过客户端、代理或网络的消费速度。无界队列把「慢」变成「内存耗尽」。

使用有界队列，并定义清楚什么可以丢。

进度是可替换的：对同一个令牌，后面的进度值取代前面的。最终 JSON-RPC 响应不可替换。

本课的缓冲区执行这套策略：

1. 合并同一令牌的相邻进度。
2. 容量到顶时丢掉最旧的进度。
3. 把流标记为「需要权威重新拉取」。
4. 保住最终响应。
5. 拒绝「保住一个最终响应就得丢掉另一个最终响应」的状态。

这是有界的丢失加显式的恢复。静默丢失不是策略。

> An SSE producer can generate progress faster than a client, proxy, or network can consume it. An unbounded queue converts slowness into memory exhaustion. ... Progress is replaceable. A later progress value supersedes an earlier one for the same token. A final JSON-RPC response is not replaceable. ... This is bounded loss with explicit recovery. Silent loss is not a strategy.

### Proxy buffering · 代理缓冲

服务端可以正确地流式输出，而反向代理却把事件扣在缓冲区里。

对 SSE 响应，发送：

```http
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

2026 版 Streamable HTTP 规范建议使用 `X-Accel-Buffering: no`，让兼容的代理立即投递事件。

对安静的长连流，周期性发出一条 SSE 注释：

```text
:
```

客户端会忽略注释行。中间设备看到了流量，就不太会关闭空闲连接。

Keepalive 不是进度。不要仅仅因为到达了一条传输层注释，就重置操作的语义空闲超时。

> A server can stream correctly while a reverse proxy holds events in a buffer. ... The 2026 Streamable HTTP specification recommends `X-Accel-Buffering: no` so compatible proxies deliver events immediately. ... The client ignores comment lines. Intermediaries see traffic and are less likely to close an idle connection. ... Keepalive is not progress. Do not reset an operation's semantic idle timeout merely because a transport comment arrived.

## Reconnect Means Refetch · 重连即重新拉取

现代 Streamable HTTP 不支持通过 `Last-Event-ID` 恢复 SSE。

`subscriptions/listen` 流断开之后：

1. 用新的 JSON-RPC id 发起一个新的 listen 请求。
2. 恢复想要的订阅过滤器。
3. 从权威方法重新拉取（refetch）受影响的工具、资源、提示（prompts）或 Task。
4. 按稳定标识符对应用状态去重。
5. 不要仅仅因为响应丢了，就重放一次不安全的变更。

示例恢复计划显式地把 `sendLastEventId` 设为 false，并列出需要重新拉取的资源。

> Modern Streamable HTTP does not support resumable SSE through `Last-Event-ID`. ... 1. Open a new listen request with a new JSON-RPC id. ... 3. Refetch affected tools, resources, prompts, or Tasks from authoritative methods. ... 5. Do not replay an unsafe mutation just because its response was lost. ... The sample recovery plan explicitly sets `sendLastEventId` to false and lists resources to refetch.

### Prevent a reconnect herd · 防止重连羊群

如果 10,000 个客户端在同一秒重连，正在恢复的服务器会再次倒下。

使用带抖动（jitter）和上限的指数退避（exponential backoff）。本课从客户端 id 和尝试次数计算确定性抖动，保证测试可复现：

```text
attempt 0: up to 250 ms
attempt 1: up to 500 ms
attempt 2: up to 1000 ms
...
cap: 8000 ms
```

生产环境可以用密码学安全的或运行时随机数。不变量是「分布开」，不是某个具体公式。

> If 10,000 clients reconnect at exactly one second, the recovering server fails again. ... Use exponential backoff with jitter and a cap. The lesson computes deterministic jitter from client id and attempt number so tests remain reproducible ... Production can use cryptographically secure or runtime randomness. The invariant is distribution, not a specific formula.

## Build It · 动手造

`code/main.py` 构建了五个小的可靠性组件。

### `RequestCoordinator` · 请求协调器

- 以空闲与最大截止时间启动一个在途请求；
- 发出单调递增的进度通知；
- 生成正确的 stdio 或 HTTP 取消信号；
- 忽略无效的取消通知；
- 把取消与完成的终态竞态显式化；
- 把服务端发起的取消保留给 stdio 订阅。

> starts an in-flight request with idle and maximum deadlines; ... makes cancellation and completion terminal races explicit; ... reserves server-sent cancellation for stdio subscriptions.

### `MutationLedger` · 变更账本

- 证明没有业务键时，两个 JSON-RPC id 会执行两次；
- 把键检查、模拟副作用、执行计数器和结果提交放进一个基于文件的 SQLite 事务；
- 在相互独立的账本连接之间，用同一个幂等键对匹配的参数去重；
- 拒绝同一个键被换参数复用；
- 返回防御性拷贝，并在重新打开后保留已提交记录。

> proves that two JSON-RPC ids execute twice without a business key; ... uses a file-backed SQLite transaction for the key check, simulated effect, execution counter, and result commit; ... returns defensive copies and preserves committed records across reopen.

### `DurableTaskService` · 持久任务服务

- 确认一次取消请求；
- 让任务在 worker 检查点之前保持 `working`；
- 解释为什么确认不等于最终状态。

> acknowledges a cancellation request; keeps the task `working` until a worker checkpoint; demonstrates why acknowledgement is not final status.

### `BoundedSseBuffer` · 有界 SSE 缓冲

- 压力下合并或丢弃进度；
- 记录「需要权威重新拉取」；
- 绝不丢弃最终响应。

> coalesces or drops progress under pressure; records that authoritative refetch is required; never drops the final response.

### Recovery helpers · 恢复辅助

- 返回代理安全的 SSE 头与 keepalive 注释；
- 创建重连与重新拉取计划；
- 用确定性的指数退避加抖动分散重试。

> return proxy-safe SSE headers and keepalive comments; create a reconnect and refetch plan; spread retries with deterministic exponential backoff and jitter.

## Use It · 实战用法

在仓库根目录执行：

```bash
cd phases/13-tools-and-protocols/29-mcp-reliability-cancellation-and-flow-control/code
python3 main.py
python3 -m unittest discover tests -v
```

演示会跑一遍中央竞态的两侧、在一个临时的基于文件的账本里执行一次事务性去重的变更、把一个有界进度缓冲压到过载，并展示一个持久 Task 从「取消已确认」走到「worker 已观察到取消」。

> The demo runs both sides of the central race, executes a transactionally deduplicated mutation in a temporary file-backed ledger, overloads a bounded progress buffer, and shows a durable Task moving from acknowledged cancellation to worker-observed cancellation.

## Interactive Lab · 交互实验

不加任何 sleep，运行四种事件顺序。

1. 启动请求 `A`，取消它，然后调用 `complete()`。
2. 启动请求 `B`，完成它，然后送达取消。
3. 启动请求 `C`，在每个空闲截止时间之前都发出进度，然后越过最大截止时间。
4. 通过 Streamable HTTP 启动请求 `D`，然后关闭它的响应流。

对每个场景记录：

- 请求的终态；
- 最终响应是否存在；
- 写上线上的取消信号；
- 客户端应当忽略哪个事件。

然后把 `D` 改成 stdio。操作完全相同，但取消信号必须改变。

> Run four event orderings without adding sleeps. ... Then change `D` to stdio. The operation is identical, but the cancellation signal must change.

## Practice Lab · 练习实验

给 `MutationLedger` 加一个 `reserve_inventory` 变更。

要求：

1. 键绑定 SKU、数量、租户（tenant）和操作名。
2. 相同键相同参数的重试返回第一次的预留。
3. 改了数量的重试直接失败，不产生新的预留。
4. 已提交但丢了响应的执行可以按键对账。
5. 结果不记录任何秘密或支付数据。
6. 客户端没有提供键时，禁用自动重试。
7. 模拟一次订阅掉线，并在决定下一步之前重新拉取库存记录。
8. 在屏障（barrier）处启动两个账本连接，并发提交相同的键。断言只提交了一个预留。
9. 改动第一个返回的预留对象。重放该键，证明存储的结果没有变化。
10. 关闭再重新打开账本文件，然后按键对账预留。

保持实验诚实：如果库存活在另一个服务里，请说明该服务是否接受相同的幂等键，还是需要事务性发件箱把本地提交桥接到远端副作用。

> Add a `reserve_inventory` mutation to `MutationLedger`. ... Keep the lab honest: if inventory lives in another service, explain whether that service accepts the same idempotency key or whether a transactional outbox bridges the local commit to the remote effect.

## Shipped Artifact · 交付物

`outputs/skill-mcp-reliability-reviewer.md` 是一个扁平的可靠性评审技能（skill）。给它一个 MCP 操作、传输、超时策略、重试行为、队列策略和恢复计划，它会返回竞态表、重试分类、幂等边界、流控检查和故障夹具（fixture）。

> `outputs/skill-mcp-reliability-reviewer.md` is a flat reliability review skill. Give it an MCP operation, transport, timeout policy, retry behavior, queue policy, and recovery plan. It returns a race table, retry classification, idempotency boundary, flow-control checks, and failure fixtures.

## Verify It · 验收

当下列陈述全部为真时，本课完成：

- stdio 取消发送 `notifications/cancelled`，且不收到任何响应。
- Streamable HTTP 取消关闭请求流，不发送取消 POST。
- 先取消后完成 → 抑制最终响应。
- 先完成后取消 → 保留响应，忽略迟到的取消。
- 进度可以重置空闲超时，但永远不能重置最大超时。
- 仅凭新的 JSON-RPC id 就会把变更再执行一遍。
- 并发双连接竞态下，一个幂等键加相同参数只执行一次。
- 已提交记录在重新打开后仍在，重放返回防御性拷贝。
- 改动一个返回结果无法改动存储结果。
- 有界缓冲保持在容量内，并保住最终响应。
- 重连使用新请求，不发送 `Last-Event-ID`，并重新拉取受影响状态。
- `tasks/cancel` 确认之后，任务在 worker 观察到之前保持非终态。

> stdio cancellation sends `notifications/cancelled` and receives no response. ... Streamable HTTP cancellation closes the request stream and sends no cancellation POST. ... Cancel-before-complete suppresses the final response. ... One idempotency key and identical arguments execute once under a concurrent two-connection race. ... Reconnect uses a new request, does not send `Last-Event-ID`, and refetches affected state. ... `tasks/cancel` acknowledgement leaves the task non-terminal until the worker observes it.

## Production Failure Modes · 生产故障模式

| 故障 | 可观察症状 | 正确响应 |
|---------|--------------------|------------------|
| HTTP 客户端 POST 取消通知 | 服务端与客户端对请求生命周期的认知不一致 | 关闭该请求的 SSE 响应流 |
| 服务端在已接受的取消之后仍响应 | 客户端收到一个不可用的迟到结果 | 取消获胜时停止工作并抑制后续消息 |
| 进度重置了每个截止时间 | 挂死的工作永远存活 | 保留一个独立的绝对最大超时 |
| 把新 RPC id 当成去重 | 扣款、部署或删除执行两次 | 增加持久的应用层幂等键 |
| 键检查与副作用分离 | 并发 worker 都观察到键缺失 | 把键认领、副作用记录和结果原子地一起提交 |
| 跨副本使用内存账本 | 重启或另一个 worker 忘掉先前的提交 | 使用共享持久存储或上游幂等 |
| 直接返回存储的可变结果 | 调用方改动污染后续重放 | 序列化已提交结果并返回防御性拷贝 |
| 同一键换了参数复用 | 一个键混叠了两个业务意图 | 存储并比较参数指纹 |
| 无界进度队列 | 慢消费者导致内存上涨 | 在有界范围内合并并丢弃可替换的进度 |
| 压力下丢弃最终响应 | 客户端无从得知请求结果 | 预留容量或驱逐进度，绝不驱逐最终响应 |
| 代理缓冲 SSE | 进度成簇到达或超时后才到达 | 关闭缓冲并配置兼容的代理超时 |
| 假设 `Last-Event-ID` 可用 | 客户端从服务端不支持的状态恢复 | 用新请求重连并重新拉取 |
| 所有客户端立即重连 | 恢复变成又一次故障 | 使用带上限、带抖动的指数退避 |
| 把任务确认当成最终取消 | UI 显示已停止而 worker 还在跑 | 轮询 Task 直到出现终态 |

> New RPC id treated as deduplication | Charge, deployment, or deletion runs twice | Add a durable application idempotency key ... Unbounded progress queue | Memory rises with a slow consumer | Coalesce and drop replaceable progress within a bound ... Every client reconnects immediately | Recovery creates another outage | Use capped exponential backoff with jitter ... Task ack treated as final cancellation | Worker keeps running after UI says stopped | Poll the Task until a terminal status

## Capstone Connection · 毕业项目关联

工具生态毕业项目（capstone）应当把可靠性当作可执行的证据，而不是架构图里的一段话。

要求这些工件（artifact）：

- 每种传输各一份取消竞态记录（transcript）；
- 每个暴露的变更一张重试表；
- 幂等键记录与不匹配夹具；
- 一份并发同键记录、一次重开检查和一次改动混叠检查；
- 一份有界缓冲过载结果；
- 反向代理 SSE 头与空闲策略；
- 一份指明权威重新拉取方法的重连计划；
- 毕业项目用到 Task 时，一份持久任务取消轨迹。

本地进程里一次绿色的请求只能证明快乐路径。当丢失的响应、迟到的取消、慢消费者和重连羊群都有确定性结果时，毕业项目才算生产就绪。

> The tool-ecosystem capstone should treat reliability as executable evidence, not a paragraph in an architecture diagram. ... A green request in a local process proves only the happy path. The capstone is production-ready when lost responses, late cancellation, slow consumers, and reconnect herds have deterministic outcomes.

## Key Terms · 术语表

| 术语 | 含义 |
|------|---------|
| Request cancellation（请求取消） | 放弃一个在途的 MCP 请求 |
| Cancellation race（取消竞态） | 终态完成事件与取消事件之间的竞争 |
| Idle timeout（空闲超时） | 自上次有效请求活动以来经过时间的上限 |
| Maximum timeout（最大超时） | 自请求开始算的绝对上限，不受进度影响 |
| Idempotency key（幂等键） | 对一个业务意图去重的应用层标识符 |
| Atomic ledger（原子账本） | 把键认领、副作用记录和结果作为一个单元提交的持久边界 |
| Backpressure（背压） | 生产者快过消费者时施加的控制 |
| Progress coalescing（进度合并） | 用更新的权威值替换较旧的进度 |
| Refetch（重新拉取） | 流中断之后重新读取当前状态 |
| Jitter（抖动） | 故意引入的变化，把重试在时间上打散 |

> Request cancellation | Abandonment of one in-flight MCP request ... Maximum timeout | Absolute limit from request start, unaffected by progress ... Idempotency key | Application identifier that deduplicates one business intent ... Jitter | Deliberate variation that spreads retries across time

## Further Reading · 延伸阅读

- [MCP Cancellation](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)
- [MCP Progress](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)
- [MCP Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [MCP Tasks Extension](https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks)
