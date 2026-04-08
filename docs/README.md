# 项目文档索引

本文档用于约束项目文档的放置位置、阅读顺序和维护规则，避免根目录继续堆积阶段性总结文件。

## 建议阅读顺序

1. `01_Product_Requirements_Document.md`
2. `02_Developer_SOP_and_Guide.md`
3. `05_Current_Feature_Status_Matrix.md`
4. `04_Database_Design.md`
5. `03_Mainland_Deployment_Guide.md`

## 文档职责

| 文档 | 作用 | 何时更新 |
|------|------|----------|
| `01_Product_Requirements_Document.md` | 产品目标、范围边界、阶段规划 | 产品范围或阶段目标变化时 |
| `02_Developer_SOP_and_Guide.md` | 开发执行规范、分层约束、交付规则 | 研发流程或技术基线变化时 |
| `03_Mainland_Deployment_Guide.md` | 大陆环境部署方式与网络适配 | 部署链路、环境变量或代理方案变化时 |
| `04_Database_Design.md` | 核心表结构与数据设计 | 模型结构或迁移策略变化时 |
| `05_Current_Feature_Status_Matrix.md` | 当前功能落地状态、测试优先级、最小回归集 | 新功能进入仓库或状态变化时 |

## 目录规则

- `docs/` 只放长期有效的基线文档。
- 阶段性总结、升级纪要、一次性方案文档统一放到 `docs/archive/<yyyy-mm>/`。
- 根目录不再新增 `*_SUMMARY.md`、`*_PLAN.md`、`*_REFERENCE.md` 这类阶段性文档。

## 维护规则

1. 任何涉及接口、运行方式、功能状态的变更，至少同步更新一份基线文档。
2. 如果文档与代码不一致，以代码实际行为为准，并在同一轮变更中修正文档。
3. 新增文档前，优先判断是否应追加到现有基线文档，而不是再开一份新的总结。
4. 归档文档默认只保留历史参考价值，不作为当前实现依据。
