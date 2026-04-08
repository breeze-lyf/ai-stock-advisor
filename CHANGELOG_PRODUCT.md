# AI 股票顾问系统 - 产品优化变更记录

> 本文档记录所有产品优化的实现细节，按时间倒序排列

---

## 2026-04-07 - Phase 1: 用户引导与认证优化

### 新增功能

#### 1. 新用户引导流程 (Onboarding)

**目标**: 降低新用户学习成本，提升留存率

**实现内容**:

1. **后端支持**
   - 新增模型：`backend/app/models/user_preference.py`
     - `UserPreference` 表：存储用户投资偏好、市场偏好、通知频率等
     - 字段包括：`investment_profile`, `preferred_markets`, `notification_frequency`, `risk_tolerance_score` 等
   - 新增 API：`backend/app/api/v1/endpoints/user_preferences.py`
     - `GET /api/v1/user-preferences/preferences` - 获取用户偏好
     - `POST /api/v1/user-preferences/onboarding` - 完成 onboarding
     - `PATCH /api/v1/user-preferences/preferences` - 更新偏好
   - 数据库迁移：`backend/migrations/versions/1a2b3c4d5e6f_add_user_preferences_table.py`
   - 路由注册：更新 `backend/app/api/v1/api.py`，添加 `user-preferences` 模块

2. **前端组件**
   - 新增向导组件：`frontend/components/features/OnboardingWizard.tsx`
     - 4 步流程：
       1. 选择投资偏好（保守/稳健/激进）
       2. 选择关注市场（A 股/港股/美股）
       3. 风险承受能力评分（1-10）
       4. 投资经验与目标收益设置
     - 响应式设计，支持暗色模式
     - 进度指示器
   - 新增页面：`frontend/app/onboarding/page.tsx`
   - API 集成：更新 `frontend/features/user/api.ts`，添加偏好相关函数

**文件清单**:
```
backend/app/models/user_preference.py              [新增]
backend/app/api/v1/endpoints/user_preferences.py   [新增]
backend/migrations/versions/1a2b3c4d5e6f_*.py      [新增]
backend/app/api/v1/api.py                          [修改]
frontend/components/features/OnboardingWizard.tsx  [新增]
frontend/app/onboarding/page.tsx                   [新增]
frontend/features/user/api.ts                      [修改]
```

---

#### 2. AI 分析系统升级 - 情景分析/风险分析/多时间框架分析

**目标**: 提升 AI 分析的专业性和可操作性，提供机构级的深度分析能力

**实现内容**:

1. **后端服务**
   - 新增服务：`backend/app/services/enhanced_ai_analysis.py`
     - `generate_scenario_analysis()` - 情景分析（乐观/基准/悲观）
     - `analyze_risk_factors()` - 风险因子分解
     - `generate_multi_timeframe_analysis()` - 多时间框架分析（短线/中线/长线）

2. **后端 API**
   - 新增端点：`backend/app/api/v1/endpoints/enhanced_analysis.py`
     - `GET /api/v1/analysis/enhanced/{ticker}/scenario-analysis` - 情景分析
     - `GET /api/v1/analysis/enhanced/{ticker}/risk-analysis` - 风险分析
     - `GET /api/v1/analysis/enhanced/{ticker}/multi-timeframe` - 多时间框架分析
     - `GET /api/v1/analysis/enhanced/{ticker}/enhanced-analysis` - 完整增强分析
   - 路由注册：更新 `backend/app/api/v1/api.py`，添加 `enhanced-analysis` 模块

3. **前端组件**
   - 情景分析组件：`frontend/components/features/stock-detail/ScenarioAnalysis.tsx`
     - 三列卡片展示三种情景
     - 显示目标价、涨跌空间、概率、时间框架
     - 核心驱动因素/风险因素列表
   - 风险分析组件：`frontend/components/features/stock-detail/RiskAnalysis.tsx`
     - 四维度风险：市场风险、技术面风险、行业风险、公司风险
     - 风险评分可视化（1-10 分）
     - β系数、RSI 等技术指标展示
   - 多时间框架组件：`frontend/components/features/stock-detail/MultiTimeframeAnalysis.tsx`
     - 短线（1-5 日）、中线（1-4 周）、长线（3-12 月）趋势判断
     - 置信度百分比
     - 关键价位（支撑/当前/阻力）
     - 策略建议

**文件清单**:
```
backend/app/services/enhanced_ai_analysis.py           [新增]
backend/app/api/v1/endpoints/enhanced_analysis.py      [新增]
backend/app/api/v1/api.py                              [修改]
frontend/components/features/stock-detail/ScenarioAnalysis.tsx    [新增]
frontend/components/features/stock-detail/RiskAnalysis.tsx        [新增]
frontend/components/features/stock-detail/MultiTimeframeAnalysis.tsx [新增]
```

**API 端点设计**:

| 方法 | 路径 | 认证 | 描述 |
|------|------|------|------|
| GET | `/api/v1/analysis/enhanced/{ticker}/scenario-analysis` | ✅ | 情景分析（乐观/基准/悲观） |
| GET | `/api/v1/analysis/enhanced/{ticker}/risk-analysis` | ✅ | 风险因子分析 |
| GET | `/api/v1/analysis/enhanced/{ticker}/multi-timeframe` | ✅ | 多时间框架分析 |
| GET | `/api/v1/analysis/enhanced/{ticker}/enhanced-analysis` | ✅ | 完整增强分析（包含以上全部） |

---

### 已完成功能（Phase 1）

- [x] 新用户引导流程
- [x] AI 分析系统升级（情景分析、风险分析、多时间框架分析）
- [x] 用户偏好设置管理

### 待实现功能（后续 Phase）

#### 通知系统升级
- [ ] 邮件通知渠道
- [ ] 浏览器推送
- [ ] 智能分级推送
- [ ] 静默时段设置

#### WebSocket 实时推送
- [ ] 连接管理
- [ ] 心跳检测
- [ ] 断线重连

#### 投资组合管理 2.0
- [ ] 风险敞口分析
- [ ] 相关性热力图
- [ ] 再平衡建议
- [ ] 业绩归因

#### 选股器
- [ ] 预设策略（低估值/成长/动量/高股息）
- [ ] 自定义条件筛选
- [ ] 结果可视化

#### 财经日历
- [ ] 宏观经济事件
- [ ] 财报季日历
- [ ] 持仓关联提醒

---

## 如何启用新功能

### 1. 应用数据库迁移

```bash
cd backend
../.venv/bin/alembic upgrade head
```

### 2. 重启后端服务

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 重启前端服务

```bash
cd frontend
npm run dev -- -p 3000
```

### 4. 测试 Onboarding 流程

1. 访问 `http://localhost:3000/register` 注册新账号
2. 注册成功后自动跳转到 `/onboarding`
3. 完成 4 步引导流程
4. 跳转回首页 `/`

---

## 技术细节

### 用户偏好数据模型设计

```python
class UserPreference(Base):
    id: str                      # UUID 主键
    user_id: str                 # 外键，关联 users 表
    investment_profile: str      # CONSERVATIVE/BALANCED/AGGRESSIVE
    preferred_markets: str       # 逗号分隔，如 "A_SHARE,US_SHARE"
    notification_frequency: str  # REALTIME/HOURLY/DAILY/NEVER
    onboarding_completed: bool   # 是否完成引导
    risk_tolerance_score: int    # 1-10
    investment_experience_years: int
    target_annual_return: int    # 百分比
```

### Onboarding Wizard 状态管理

```typescript
interface OnboardingData {
    investmentProfile: InvestmentProfile;
    preferredMarkets: MarketPreference[];
    notificationFrequency: NotificationFrequency;
    riskToleranceScore: number;
    investmentExperienceYears: number;
    targetAnnualReturn: number;
}
```

### API 端点设计

| 方法 | 路径 | 认证 | 描述 |
|------|------|------|------|
| GET | `/api/v1/user-preferences/preferences` | ✅ | 获取用户偏好 |
| POST | `/api/v1/user-preferences/onboarding` | ✅ | 完成 onboarding |
| PATCH | `/api/v1/user-preferences/preferences` | ✅ | 部分更新偏好 |

---

## 后续优化建议

### 短期（1-2 周）
1. 在注册后自动检测 `onboarding_completed` 状态，未完成的跳转到引导页
2. 添加 onboarding 完成率统计
3. 优化引导文案和视觉设计

### 中期（1 个月）
1. 根据用户偏好个性化首页内容
2. 根据风险评分推荐股票
3. A/B 测试不同引导流程的转化率

### 长期（3 个月）
1. 引入更多个性化设置（主题色、布局等）
2. 用户画像系统
3. 智能推荐引擎

---

## 问题反馈

如发现问题，请在 GitHub 仓库提交 Issue，或联系开发团队。
