# 项目文档索引

本文档是 `docs/` 的导航页，用来回答三个问题：

- 新人或 AI 编程助手应该先读哪些文档。
- 每份文档负责什么，不负责什么。
- 文档变多时如何更新、归档和避免重复。

当前 `docs/` 顶层只保留日常高频基线文档。产品侧长文档放在 `docs/product/`，阶段性总结、一次性方案和历史材料应放到 `docs/archive/<yyyy-mm>/`。

## 快速阅读路径

### 1. 新人了解项目

1. `../README.md` — 项目首页、快速启动、技术栈和协作入口。
2. `05_Current_Feature_Status_Matrix.md` — 先看哪些功能真的已经落地。
3. `09_Architecture_Overview.md` — 看系统架构图和核心流程图。
4. `02_Developer_SOP_and_Guide.md` — 再看开发规则、分层和交付要求。

### 2. 开始写代码

1. `02_Developer_SOP_and_Guide.md` — 开发流程、分层红线、迁移和测试规则。
2. `05_Current_Feature_Status_Matrix.md` — 确认要改的功能状态和测试优先级。
3. `04_Database_Design.md` — 只有涉及模型、迁移、数据契约时必读。
4. `09_Architecture_Overview.md` — 涉及跨模块流程、架构图或 Module/Seam 时必读。

### 3. 做 AI / Agent 相关能力

1. `09_Architecture_Overview.md` — 先看当前 AI 调用、BYOK、行情和通知主流程。
2. `06_AI_Analysis_Implementation_Guide.md` — 看增强分析页面和实现细节。
3. `07_Agent_Architecture_Design.md` — 看工具增强型 Agent 的任务拆解和输出格式。
4. `08_Agent_Decision_Log.md` — 看长期架构假设、设计取舍和 AI 协作决策。

### 4. 部署或排查线上问题

1. `03_Mainland_Deployment_Guide.md` — 大陆部署、网络、代理、ACR、docker-compose。
2. `05_Current_Feature_Status_Matrix.md` — 看运行环境核查和最小回归集。
3. `02_Developer_SOP_and_Guide.md` — 看统一启动和质量要求。

## 文档分层

### 日常必读

| 文档 | 作用 | 适用场景 |
|------|------|----------|
| `../README.md` | 项目首页 | 每次进项目先定位 |
| `02_Developer_SOP_and_Guide.md` | 开发执行规范 | 写代码、改接口、提测前 |
| `05_Current_Feature_Status_Matrix.md` | 当前功能状态 | 判断功能是否已完成、部分完成或只是骨架 |
| `09_Architecture_Overview.md` | 架构地图和 Mermaid 图 | 理解系统、跨模块改动、画图、架构评审 |

### 按需参考

| 文档 | 作用 | 适用场景 |
|------|------|----------|
| `product/README.md` | 产品文档入口和短版产品基线 | 产品范围、商业化、长期规划讨论 |
| `product/01_Product_Requirements_Document.md` | 完整 PRD | 需要详细用户研究、产品规划、商业化和风险分析时 |
| `03_Mainland_Deployment_Guide.md` | 大陆网络与生产部署 | 部署、代理、ACR、服务器排障 |
| `04_Database_Design.md` | 数据库结构与数据契约 | ORM、Alembic、表结构、数据生命周期 |
| `06_AI_Analysis_Implementation_Guide.md` | AI 增强分析实现指南 | 增强分析、催化剂、关键假设、组合联动 |
| `07_Agent_Architecture_Design.md` | Agent 任务拆解和输出规范 | Tool-Augmented Agent、新 Agent 功能 |

### 长期记忆

| 文档 | 作用 | 更新方式 |
|------|------|----------|
| `08_Agent_Decision_Log.md` | AI 协作中的长期决定、现实假设和架构权衡 | 只追加影响后续开发判断的决定 |

## 文档职责

| 文档 | 负责 | 不负责 | 何时更新 |
|------|------|--------|----------|
| `product/README.md` | 短版产品基线和产品文档导航 | 当前实现状态的最终判断 | 产品定位或产品文档结构变化时 |
| `product/01_Product_Requirements_Document.md` | 产品目标、用户画像、长期规划、完整 PRD | 当前实现状态的最终判断 | 产品范围或阶段目标变化时 |
| `02_Developer_SOP_and_Guide.md` | 开发流程、分层约束、交付规则 | 详细产品愿景 | 研发流程或技术基线变化时 |
| `03_Mainland_Deployment_Guide.md` | 部署链路、大陆网络、代理和运维排障 | 本地日常开发细节 | 部署、环境变量或代理方案变化时 |
| `04_Database_Design.md` | 核心表结构、数据契约、迁移意图 | 全量功能路线图 | 模型结构或迁移策略变化时 |
| `05_Current_Feature_Status_Matrix.md` | 当前交付状态、测试优先级、最小回归集 | 长期愿景和历史方案 | 新功能进入仓库或状态变化时 |
| `06_AI_Analysis_Implementation_Guide.md` | AI 增强分析实现方案 | 全系统架构总览 | 增强分析模块实现或重构时 |
| `07_Agent_Architecture_Design.md` | Agent 任务拆解、输出格式、工具增强型范式 | 当前所有服务调用关系 | Agent 能力开发或架构调整时 |
| `08_Agent_Decision_Log.md` | 长期决定、假设、权衡 | 普通代码改动流水账 | 每次会话产生长期有效决定时 |
| `09_Architecture_Overview.md` | 系统架构、核心 Module、关键 Mermaid 图 | 详细 PRD 和测试清单 | 架构 Module、核心流程或外部依赖变化时 |

## 当前优化判断

- `product/01_Product_Requirements_Document.md` 很长，适合作为产品参考库，不适合作为日常必读入口。
- `06_AI_Analysis_Implementation_Guide.md` 和 `07_Agent_Architecture_Design.md` 有重叠，但职责不同：前者偏实现指南，后者偏 Agent 范式和输出契约。
- `09_Architecture_Overview.md` 是当前架构图入口。以后不要再新增零散的 `ARCHITECTURE_SUMMARY.md` 或 `FLOW_CHART.md`。
- `08_Agent_Decision_Log.md` 只记录长期有效决定，不记录普通任务过程。

## 维护规则

1. 新功能进入仓库后，优先更新 `05_Current_Feature_Status_Matrix.md`。
2. 接口、运行方式、分层规则变化时，更新 `02_Developer_SOP_and_Guide.md`。
3. 架构 Module、核心流程、外部 Provider 或调度策略变化时，更新 `09_Architecture_Overview.md`。
4. 数据库模型或迁移策略变化时，更新 `04_Database_Design.md`。
5. AI/Agent 长期设计决定变化时，追加到 `08_Agent_Decision_Log.md`。
6. 新增文档前，先判断能否追加到现有基线文档。
7. 根目录不新增 `*_SUMMARY.md`、`*_PLAN.md`、`*_REFERENCE.md` 这类阶段性文档。
8. 归档文档默认只保留历史参考价值，不作为当前实现依据。

## 建议的后续深度优化

下一步如果要继续瘦身，可以考虑：

- 把 `06` 和 `07` 中重复的 Agent 架构描述合并到 `09`，让 `06` 只保留实现步骤。
- 为 `docs/archive/` 建一个归档索引，记录历史文档为什么不再作为当前依据。
