# Security — Secrets, API Key Rotation, Audit Logs, Guardrails · 安全——密钥、API Key 轮换、审计日志与护栏

> 用集中式密钥库（vault：HashiCorp Vault、AWS Secrets Manager、Azure Key Vault）消灭密钥散落。绝不要把凭据存进配置文件、纳入版本控制的 env 文件或电子表格。用 IAM 角色取代静态密钥；CI/CD 用 OIDC。AI 网关（AI-gateway）模式是 2026 年的标准解法：应用 → 网关 → 模型供应商，网关在运行时从 vault 拉取凭据。在 vault 里轮换，所有应用几分钟内自动生效——不用重新部署，也不用再发「谁有新 key」的 Slack 消息。轮换策略 ≤90 天；每次提交都用 TruffleHog / GitGuardian / Gitleaks 扫描。零信任（zero-trust）：MFA、SSO、RBAC/ABAC、短时效 token、设备态势（device posture）。PII 清洗（scrubbing）用实体识别在转发前遮蔽 PHI/PII；一致性令牌化（consistent tokenization，Mesh 方案）把敏感值映射成稳定的占位符，让 LLM 保住代码 / 关系语义。网络出口（egress）：LLM 服务放进专用 VPC/VNet 子网，白名单只有 `api.openai.com`、`api.anthropic.com` 等；其余出站全部阻断。2026 年的标志性事件：Vercel 供应链攻击——CI/CD 凭据失窃，数千个客户部署的环境变量被外泄。

> Eliminate secret sprawl via centralized vaults (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault). Never store credentials in config files, env files in VCS, spreadsheets. Use IAM roles over static keys; OIDC for CI/CD. The AI-gateway pattern is the 2026 solution: apps → gateway → model provider, with gateway pulling credentials from vault at runtime. Rotate in vault and all apps pick up in minutes — no redeploys, no Slack "who has the new key" messages. Rotation policy ≤90 days; scan with TruffleHog / GitGuardian / Gitleaks on every commit. Zero-trust: MFA, SSO, RBAC/ABAC, short-lived tokens, device posture. PII scrubbing uses entity recognition to mask PHI/PII before forwarding; consistent tokenization (Mesh approach) maps sensitive values to stable placeholders so the LLM preserves code/relationship semantics. Network egress: LLM services in dedicated VPC/VNet subnet whitelisting only `api.openai.com`, `api.anthropic.com` etc; block all other outbound. The 2026 incident driver: Vercel supply-chain attack via compromised CI/CD credentials exfiltrated env vars across thousands of customer deployments.

**Type:** Learn
**Languages:** Python (stdlib, toy PII-scrubber + audit-log writer)
**Prerequisites:** Phase 17 · 19 (AI Gateways), Phase 17 · 13 (Observability)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 列举四种密钥管理反模式（纳入版本控制的配置文件、硬编码环境变量、电子表格、静态密钥），并说出各自的替代方案
- 解释「AI 网关从 vault 拉取凭据」模式作为 2026 年的生产标准
- 实现一个带一致性令牌化（consistent tokenization，相同值 → 相同占位符）的 PII 清洗器，让语义得以保留
- 说出 2026 年 Vercel 供应链事件，以及它给 CI/CD 凭据卫生的教训

> Enumerate the four secret-management anti-patterns (config files in VCS, hardcoded env, spreadsheets, static keys) and name their replacements.
> Explain the AI-gateway-pulls-from-vault pattern as 2026 production standard.
> Implement a PII scrubber with consistent tokenization (same value → same placeholder) so semantics survive.
> Name the 2026 Vercel supply-chain incident and what it taught about CI/CD credential hygiene.

---

## The Problem · 问题在哪

一个实习生把带 API key 的 `.env` 提交了进来。他很快删掉了。但 key 已经进了 git 历史——GitGuardian 扫描逮到了它，而你的轮换流程是「Slack 通知全组、更新 40 个配置文件、重新部署所有服务」。8 小时后，一半服务已经用上新 key，另一半还在等部署窗口。

另一件事：用户提示词里出现「My SSN is 123-45-6789」。提示词被发给了 OpenAI。你有 BAA，但内部政策要求转发前遮蔽 PII。你没做。

第三件事：你 EKS 集群里的 LLM pod 可以访问任意互联网主机。有人通过向攻击者控制的域名发 DNS 查询外泄了数据。没有任何东西拦截它。

LLM 服务的安全必须同时覆盖这三个向量：vault 托管的凭据、PII 清洗、网络出口过滤、审计日志。

> An intern commits `.env` with API keys. They delete it quickly. The keys are already in git history — GitGuardian scan catches it, your rotation process is "Slack the team, update 40 config files, redeploy all services." 8 hours later, half your services are live and half are waiting for deploy windows. ... Security for LLM services has to address all three vectors. Vault-backed credentials. PII scrubbing. Network egress filtering. Audit logs.

---

## The Concept · 概念

### Centralized vault + IAM-role pull · 集中式 vault + IAM 角色拉取

**Vault**：HashiCorp Vault、AWS Secrets Manager、Azure Key Vault、GCP Secret Manager。唯一事实来源（single source of truth）。

**IAM 角色**：应用 / 网关用它的 IAM 身份认证，而不是静态 key。vault 在 token 有效期内返回密钥。

**AI 网关模式**：网关在请求时从 vault 拉取 `OPENAI_API_KEY`。在 vault 里轮换；下一个请求就拿到新 key。无需重新部署。

> **Vault**: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager. One source of truth. ... **The AI-gateway pattern**: gateway pulls `OPENAI_API_KEY` from vault at request time. Rotate in vault; next request gets the new key. No redeploys.

### Rotation policy ≤ 90 days · 轮换策略 ≤ 90 天

覆盖所有 API key、vault root token、CI/CD 凭据。能自动轮换的就自动轮换。手动轮换要记录并跟踪。

> All API keys, vault root tokens, CI/CD credentials. Automated rotation where possible. Manual rotation logged and tracked.

### Secret scanning · 密钥扫描

- **TruffleHog**——对提交做正则 + 熵检测。
- **GitGuardian**——商业产品，准确率高。
- **Gitleaks**——开源，可在 CI 里跑。

每次提交都扫描。检测到新密钥就阻断 PR。

> **TruffleHog** — regex + entropy on commits. ... **GitGuardian** — commercial, high accuracy. ... **Gitleaks** — OSS, runs in CI.
> Run on every commit. Block PR if new secret detected.

### Zero-trust posture · 零信任姿态

- 所有账号强制 MFA。
- 通过 SAML/OIDC 做 SSO。
- 细粒度访问控制用 RBAC（基于角色）或 ABAC（基于属性）。
- 短时效 token（按小时计，不是按天）。
- 设备态势（device posture）——只允许开了磁盘加密的公司设备。

> MFA required on all accounts. ... RBAC (role-based) or ABAC (attribute-based) for fine grained access. ... Short-lived tokens (hours, not days). ... Device posture — only corp devices with disk encryption.

### PII / PHI scrubbing · PII / PHI 清洗

在提示词离开你的基础设施之前：

1. 实体识别（spaCy NER、Presidio、商业产品）。
2. 遮蔽命中的实体：`"My SSN is 123-45-6789"` → `"My SSN is [SSN_TOKEN_A3F]"`。
3. 一致性令牌化（Mesh 方案）：相同的值映射到相同的占位符，让 LLM 保住关系。
4. 可选：对 LLM 响应做反向映射。

静态正则过滤器能抓基本模式；NER 能抓更多。两个都用。

> Before the prompt leaves your infra:
> 1. Entity recognition (spaCy NER, Presidio, commercial).
> 2. Mask matched entities: `"My SSN is 123-45-6789"` → `"My SSN is [SSN_TOKEN_A3F]"`.
> 3. Consistent tokenization (Mesh approach): same value maps to the same placeholder so the LLM preserves relationships.
> 4. Optional reverse mapping for LLM response.
> Static regex filters catch basic patterns; NER catches more. Use both.

### Input + output guardrails · 输入 + 输出护栏

输入：拦截已知越狱（jailbreak）和违禁话题；按用户限流。

输出：用正则清洗泄漏的密钥（API key 模式、拒绝语境里的邮箱模式）；用分类器检测政策违规。

> Input: block known jailbreaks, forbidden topics; rate-limit per-user.
> Output: regex scrub for leaked secrets (API key patterns, email patterns in refusal contexts), classifier for policy violations.

### Network egress whitelist · 网络出口白名单

LLM 服务放进专用子网：
- 白名单：`api.openai.com`、`api.anthropic.com`、向量库端点、vault 端点。
- 其余一律丢弃。
- DNS 走只认白名单的解析器（防 DNS 隧道外泄）。

> LLM services in a dedicated subnet:
> - Whitelist: `api.openai.com`, `api.anthropic.com`, vector DB endpoints, vault endpoints.
> - Everything else: drop.
> - DNS via allowlist-only resolver (avoid DNS-tunneling exfil).

### Audit log · 审计日志

每次 LLM 调用的不可篡改日志，包含：
- 时间戳。
- 用户 / 租户。
- 提示词哈希（出于隐私，不存原始提示词）。
- 模型 + 版本。
- token 计数。
- 成本。
- 响应哈希。
- 触发的护栏。

按法规要求保留（SOC 2 保 1 年，HIPAA 保 6 年）。

> Immutable log of every LLM call with:
> - Timestamp.
> - User / tenant.
> - Prompt hash (not raw prompt for privacy).
> - Model + version.
> - Token counts.
> - Cost.
> - Response hash.
> - Any guardrail trips.
> Retain per regulatory requirement (SOC 2 1 year, HIPAA 6 years).

### The 2026 Vercel incident · 2026 年 Vercel 事件

供应链攻击：失窃的 CI/CD 凭据把数千个客户部署的环境变量外泄。教训：CI/CD 凭据等同生产凭据。存进 vault。权限范围收窄。勤轮换。

> Supply-chain attack: compromised CI/CD credentials exfiltrated env vars across thousands of customer deployments. Lesson: CI/CD credentials are prod-equivalent. Store in vault. Scope narrowly. Rotate aggressively.

### Numbers you should remember · 该记住的数字

- 轮换策略：≤ 90 天。
- 每次提交都扫描：TruffleHog / GitGuardian / Gitleaks。
- Vercel 2026：CI/CD 凭据失窃 → 数千客户的环境变量泄漏。
- 审计日志保留期：SOC 2 = 1 年，HIPAA = 6 年。

> Rotation policy: ≤ 90 days.
> Scan on every commit: TruffleHog / GitGuardian / Gitleaks.
> Vercel 2026: CI/CD creds compromised → thousands of customer env vars leaked.
> Audit log retention: SOC 2 = 1 year, HIPAA = 6 years.

```figure
i4-vault-rotation
```

---

## Use It · 实战用法

`code/main.py` 实现了一个玩具版 PII 清洗器（带一致性令牌化）和一个只追加（append-only）的审计日志。

> `code/main.py` implements a toy PII scrubber with consistent tokenization and an append-only audit log.

---

## Ship It · 交付

本课产出 `outputs/skill-llm-security-plan.md`。输入合规范围和现状，它规划 vault 迁移、清洗器、出口管控和审计日志。

> This lesson produces `outputs/skill-llm-security-plan.md`. Given regulatory scope and current state, plans the vault migration, scrubber, egress, audit log.

---

## Exercises · 练习

1. 跑 `code/main.py`。发两条引用同一个 SSN 的提示词，确认两者拿到相同的占位符。
2. 为一个调用 OpenAI + Anthropic + Weaviate 的 vLLM-on-EKS 部署设计网络出口策略。
3. 你在 git 历史里发现一个 key（2 年前的）。正确的响应是什么——轮换 key、清洗历史，还是两者都做？给出理由。
4. 你的审计日志每天涨 10 GB。设计保留分层（热 30 天、温 12 个月、冷 6 年）。
5. 论证反向令牌化（把真实值替换回 LLM 响应）是否值得引入这份复杂度，还是让占位符保持可见就好。

---

## Key Terms · 术语表

| 术语 | 人们口头说 | 实际含义 |
|------|----------------|------------------------|
| Vault | 「密钥库」 | 集中式凭据管理服务 |
| IAM role | 「基于身份的认证」 | 应用假定的角色；返回短时效凭据 |
| OIDC for CI/CD | 「云签发的 token」 | CI 里不用静态 key——用 OIDC 身份 |
| TruffleHog / GitGuardian / Gitleaks | 「密钥扫描器」 | 提交时的密钥检测 |
| RBAC / ABAC | 「访问控制」 | 基于角色 vs 基于属性 |
| PII scrubbing | 「数据遮蔽」 | 移除或令牌化敏感实体 |
| Consistent tokenization | 「稳定占位符」 | 相同的值每次都映射到相同的 token |
| Mesh approach | 「Mesh 令牌化」 | 保语义的令牌化模式 |
| Egress whitelist | 「出站白名单」 | 只有被允许的域名可达 |
| Audit log | 「不可篡改的历史」 | 面向合规的只追加记录 |

---

## Further Reading · 延伸阅读

- [Doppler — Advanced LLM Security](https://www.doppler.com/blog/advanced-llm-security)
- [Portkey — Manage LLM API keys with secret references](https://portkey.ai/blog/secret-references-ai-api-key-management/)
- [Datadog — LLM Guardrails Best Practices](https://www.datadoghq.com/blog/llm-guardrails-best-practices/)
- [JumpServer — Secrets Management Best Practices 2026](https://www.jumpserver.com/blog/secret-management-best-practices-2026)
- [Microsoft Presidio](https://github.com/microsoft/presidio) —— PII 检测与匿名化
- [HashiCorp Vault docs](https://developer.hashicorp.com/vault/docs)
