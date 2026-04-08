# AI 股票顾问系统 - 产品升级快速参考

> 快速查看本次升级的所有变更和新功能

---

## 📁 新增文件清单

### 后端文件 (5 个)

```
backend/app/models/user_preference.py              # 用户偏好模型
backend/app/api/v1/endpoints/user_preferences.py   # 用户偏好 API
backend/app/services/enhanced_ai_analysis.py       # 增强 AI 分析服务
backend/app/api/v1/endpoints/enhanced_analysis.py  # 增强分析 API
backend/app/services/email_service.py              # 邮件通知服务
```

### 前端文件 (7 个)

```
frontend/app/onboarding/page.tsx                              # Onboarding 页面
frontend/components/features/OnboardingWizard.tsx             # Onboarding 向导组件
frontend/components/features/stock-detail/ScenarioAnalysis.tsx    # 情景分析组件
frontend/components/features/stock-detail/RiskAnalysis.tsx        # 风险分析组件
frontend/components/features/stock-detail/MultiTimeframeAnalysis.tsx # 多时间框架组件
```

### 文档文件 (4 个)

```
PRODUCT_OPTIMIZATION_PLAN.md         # 产品优化计划（完整蓝图）
CHANGELOG_PRODUCT.md                 # 产品变更记录（详细历史）
SYSTEM_UPGRADE_SUMMARY.md            # 系统升级总结（本文档的完整版）
PRODUCT_UPGRADE_QUICK_REFERENCE.md   # 快速参考（当前文件）
```

### 数据库迁移 (1 个)

```
backend/migrations/versions/1a2b3c4d5e6f_add_user_preferences_table.py
```

---

## 🚀 快速开始

### 1. 应用数据库迁移

```bash
cd backend
../.venv/bin/alembic upgrade head
```

### 2. 启动后端服务

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 启动前端服务

```bash
cd frontend
npm run dev -- -p 3000
```

---

## 📡 新增 API 端点

### 用户偏好 (User Preferences)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/user-preferences/preferences` | 获取用户偏好 |
| POST | `/api/v1/user-preferences/onboarding` | 完成 onboarding |
| PATCH | `/api/v1/user-preferences/preferences` | 更新偏好 |

### 增强分析 (Enhanced Analysis)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/analysis/enhanced/{ticker}/scenario-analysis` | 情景分析 |
| GET | `/api/v1/analysis/enhanced/{ticker}/risk-analysis` | 风险分析 |
| GET | `/api/v1/analysis/enhanced/{ticker}/multi-timeframe` | 多时间框架分析 |
| GET | `/api/v1/analysis/enhanced/{ticker}/enhanced-analysis` | 完整增强分析 |

---

## 🧪 测试指南

### 测试 Onboarding 流程

1. 访问 `http://localhost:3000/register` 注册新账号
2. 注册成功后自动跳转到 `/onboarding`
3. 完成 4 步引导流程：
   - Step 1: 选择投资偏好（保守/稳健/激进）
   - Step 2: 选择关注市场（A 股/港股/美股）
   - Step 3: 风险承受能力评分（1-10）
   - Step 4: 投资经验与目标收益设置
4. 跳转回首页 `/`

### 测试增强分析

1. 访问任意股票详情页（如 `/stock/AAPL`）
2. 点击"开启深度诊断"按钮
3. 等待 AI 分析完成（约 60-120 秒）
4. 查看新增的分析卡片：
   - 情景分析（乐观/基准/悲观）
   - 风险分析（四维度评估）
   - 多时间框架分析（短线/中线/长线）

### 测试邮件通知（需配置 SMTP）

1. 设置环境变量：
```bash
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your_email@gmail.com
export SMTP_PASSWORD=your_app_password
export FROM_EMAIL=noreply@yourdomain.com
export EMAIL_ENABLED=true
```

2. 重启后端服务
3. 触发价格预警或每日报告

---

## 📊 功能对比

| 功能 | 升级前 | 升级后 |
|------|--------|--------|
| 新用户引导 | ❌ 无 | ✅ 4 步交互式 |
| 情景分析 | ❌ 无 | ✅ 三情景分析 |
| 风险分析 | ⚠️ 基础 | ✅ 四维度评估 |
| 时间框架分析 | ❌ 单一 | ✅ 三时间框架 |
| 通知渠道 | 1 个 (飞书) | 2 个 (飞书 + 邮件) |
| 用户偏好管理 | ⚠️ 基础 | ✅ 完整体系 |

---

## 🔧 配置说明

### 邮件服务配置

在 `backend/.env` 中添加：

```bash
# 邮件服务配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password  # 使用应用专用密码
FROM_EMAIL=noreply@yourdomain.com
EMAIL_ENABLED=true
```

### Onboarding 配置

Onboarding 功能默认启用，无需额外配置。

---

## 📝 数据库变更

### 新增表：user_preferences

```sql
CREATE TABLE user_preferences (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR UNIQUE NOT NULL,
    investment_profile VARCHAR NOT NULL DEFAULT 'BALANCED',
    preferred_markets VARCHAR NOT NULL DEFAULT 'A_SHARE',
    notification_frequency VARCHAR NOT NULL DEFAULT 'REALTIME',
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    risk_tolerance_score INTEGER NOT NULL DEFAULT 5,
    investment_experience_years INTEGER NOT NULL DEFAULT 0,
    target_annual_return INTEGER NOT NULL DEFAULT 10,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX ix_user_preferences_user_id ON user_preferences(user_id);
```

---

## 🐛 已知问题

### 待修复

- [ ] Onboarding 完成后需要手动跳转到首页（应自动跳转）
- [ ] 增强分析组件未集成到个股分析页（需要手动调用 API）

### 计划中

- [ ] WebSocket 实时推送
- [ ] 投资组合风险敞口可视化
- [ ] 选股器功能

---

## 📚 相关文档

- **产品优化计划**: `PRODUCT_OPTIMIZATION_PLAN.md` - 完整的产品优化路线图
- **变更记录**: `CHANGELOG_PRODUCT.md` - 详细的变更历史
- **升级总结**: `SYSTEM_UPGRADE_SUMMARY.md` - 完整的技术总结

---

## 💡 使用技巧

### 1. 快速测试所有增强分析

```bash
# 使用 curl 调用完整增强分析 API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/analysis/enhanced/AAPL/enhanced-analysis
```

### 2. 查看 Swagger API 文档

访问 `http://localhost:8000/docs` 查看完整的 API 文档

### 3. 重置 Onboarding 状态

```sql
-- 在数据库中执行
UPDATE user_preferences SET onboarding_completed = false WHERE user_id = 'YOUR_USER_ID';
```

---

## 📞 支持与反馈

- **提交 Issue**: GitHub 仓库
- **技术文档**: 查看各模块的源文件注释
- **产品讨论**: 查看 `PRODUCT_OPTIMIZATION_PLAN.md`

---

© 2026 AI Smart Investment Advisor - 让决策更理智
