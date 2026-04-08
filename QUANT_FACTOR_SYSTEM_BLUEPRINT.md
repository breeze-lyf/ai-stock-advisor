# 量化因子交易系统实现蓝图

> **版本**: 1.0
> **创建日期**: 2026-04-07
> **目标**: 构建专业级量化因子挖掘、回测、交易系统

---

## 一、系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端展示层                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ 因子库   │  │ 因子研究 │  │ 组合构建 │  │ 实盘监控 │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        API 网关层                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ 因子 API │  │ 回测 API │  │ 交易 API │  │ 风控 API │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        核心服务层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 因子引擎     │  │ 组合优化器   │  │ 风控引擎     │          │
│  │ - 因子计算   │  │ - 均值方差   │  │ - 仓位控制   │          │
│  │ - 因子合成   │  │ - Black-Litt │  │ - 止损止盈   │          │
│  │ - 因子筛选   │  │ - Risk Parity│  │ - 敞口限制   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 信号引擎     │  │ 执行引擎     │  │ 绩效归因     │          │
│  │ - 信号生成   │  │ - 订单拆分   │  │ - Brinson    │          │
│  │ - 信号组合   │  │ - 算法交易   │  │ - 因子贡献   │          │
│  │ - 信号衰减   │  │ - VWAP/TWAP  │  │ - 风险贡献   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        数据层                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ 行情数据 │  │ 财务数据 │  │ 因子数据 │  │ 交易数据 │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、核心模块设计

### 2.1 因子库 (Factor Library)

#### 因子分类体系

```python
# 因子大类
FACTOR_CATEGORIES = {
    "MOMENTUM": "动量因子",
    "VALUE": "价值因子",
    "GROWTH": "成长因子",
    "QUALITY": "质量因子",
    "VOLATILITY": "波动率因子",
    "SIZE": "规模因子",
    "LIQUIDITY": "流动性因子",
    "TECHNICAL": "技术因子",
    "SENTIMENT": "情绪因子",
}
```

#### 因子数据模型

```python
class Factor(Base):
    __tablename__ = "factors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)  # 因子名称
    category: Mapped[str] = mapped_column(String(50))  # 因子类别
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # 因子计算配置
    calculation_params: Mapped[Dict] = mapped_column(JSON)
    lookback_period: Mapped[int] = mapped_column(Integer)  # 回溯期
    decay_period: Mapped[int] = mapped_column(Integer)  # 衰减期
    
    # 因子表现
    ic_mean: Mapped[Optional[float]] = mapped_column(Numeric(8, 6))  # IC 均值
    ic_ir: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))  # ICIR
    annual_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    max_drawdown: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)


class FactorValue(Base):
    """因子值存储（横截面数据）"""
    __tablename__ = "factor_values"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    factor_id: Mapped[str] = mapped_column(ForeignKey("factors.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[Optional[float]] = mapped_column(Numeric(18, 8))
    zscore_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))  # 标准化值
    rank_value: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))  # 排序值 (0-1)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('factor_id', 'ticker', 'trade_date'),
    )
```

#### 预设因子实现

```python
# backend/app/services/factors/preset_factors.py

class PresetFactors:
    """预设因子库"""
    
    @staticmethod
    def momentum_12m(ticker: str, lookback: int = 252) -> pd.Series:
        """12 个月动量因子（20 日）"""
        # 公式：(当前价格 - 12 月前价格) / 12 月前价格
        pass
    
    @staticmethod
    def momentum_1m_exclude_1d(ticker: str) -> pd.Series:
        """1 个月动量（剔除最近 1 日）"""
        # 公式：(20 日前价格 - 1 日前价格) / 1 日前价格
        pass
    
    @staticmethod
    def value_pe(ticker: str) -> pd.Series:
        """PE 价值因子"""
        # 公式：-ln(PE) 或 EP = 1/PE
        pass
    
    @staticmethod
    def value_pb(ticker: str) -> pd.Series:
        """PB 价值因子"""
        # 公式：-ln(PB) 或 BP = 1/PB
        pass
    
    @staticmethod
    def growth_revenue(ticker: str, periods: int = 4) -> pd.Series:
        """营收增速因子"""
        # 公式：YoY 营收增长率
        pass
    
    @staticmethod
    def growth_earnings(ticker: str, periods: int = 4) -> pd.Series:
        """盈利增速因子"""
        # 公式：YoY 净利润增长率
        pass
    
    @staticmethod
    def quality_roe(ticker: str) -> pd.Series:
        """ROE 质量因子"""
        # 公式：ROE (TTM)
        pass
    
    @staticmethod
    def quality_gross_margin(ticker: str) -> pd.Series:
        """毛利率因子"""
        # 公式：毛利率 (TTM)
        pass
    
    @staticmethod
    def volatility_20d(ticker: str) -> pd.Series:
        """20 日波动率因子"""
        # 公式：20 日收益率标准差 * sqrt(252)
        pass
    
    @staticmethod
    def turnover_ratio(ticker: str, lookback: int = 20) -> pd.Series:
        """换手率因子"""
        # 公式：20 日平均换手率
        pass
    
    @staticmethod
    def rsrs(ticker: str, lookback: int = 17) -> pd.Series:
        """RSRS 因子（阻力支撑相对强度）"""
        # 公式：RSRS = slope / std(slope)
        pass
```

---

### 2.2 因子研究引擎 (Factor Research Engine)

```python
# backend/app/services/factors/factor_research.py

class FactorResearchEngine:
    """
    因子研究引擎
    
    功能：
    1. IC 分析（Rank IC, Normal IC）
    2. 因子自相关性
    3. 因子分层回测
    4. 因子正交化
    5. 因子衰减分析
    """

    @staticmethod
    async def calculate_ic(
        factor_values: pd.Series,
        forward_returns: pd.Series,
        method: str = "rank",
    ) -> float:
        """
        计算 IC（信息系数）
        
        Args:
            factor_values: 因子值序列
            forward_returns: 前瞻收益序列
            method: "rank" 或 "normal"
        
        Returns:
            IC 值
        """
        pass

    @staticmethod
    async def calculate_icir(ic_series: pd.Series) -> float:
        """计算 ICIR（IC 信息率）"""
        # ICIR = mean(IC) / std(IC) * sqrt(252)
        pass

    @staticmethod
    async def factor_backtest_layered(
        factor_values: pd.DataFrame,  # index=date, columns=ticker
        prices: pd.DataFrame,
        n_layers: int = 10,
    ) -> Dict[str, pd.Series]:
        """
        因子分层回测
        
        Returns:
            {"layer_1": equity_curve, "layer_2": ..., "layer_10": ...}
        """
        pass

    @staticmethod
    async def calculate_factor_turnover(factor_values: pd.DataFrame) -> float:
        """计算因子换手率"""
        pass

    @staticmethod
    async def orthogonalize_factor(
        target_factor: pd.Series,
        orthogonal_factors: List[pd.Series],
    ) -> pd.Series:
        """
        因子正交化（去除已知因子影响）
        
        使用 Gram-Schmidt 正交化或回归残差法
        """
        pass

    @staticmethod
    async def factor_decay_analysis(
        factor_values: pd.DataFrame,
        prices: pd.DataFrame,
        max_lag: int = 20,
    ) -> pd.Series:
        """
        因子衰减分析
        
        Returns:
            IC 随滞后期的变化曲线
        """
        pass
```

---

### 2.3 因子合成引擎 (Factor Combination Engine)

```python
# backend/app/services/factors/factor_combination.py

class FactorCombinationEngine:
    """
    因子合成引擎
    
    功能：
    1. 等权合成
    2. IC 加权合成
    3. 机器学习合成（回归/LGBM）
    4. 动态权重优化
    """

    @staticmethod
    def equal_weight_combine(
        factor_data: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """等权合成因子"""
        pass

    @staticmethod
    def ic_weight_combine(
        factor_data: Dict[str, pd.DataFrame],
        ic_scores: Dict[str, float],
    ) -> pd.DataFrame:
        """IC 加权合成"""
        # weight_i = IC_i / sum(IC)
        pass

    @staticmethod
    def regression_combine(
        factor_data: Dict[str, pd.DataFrame],
        target_returns: pd.DataFrame,
        lookback: int = 252,
    ) -> pd.DataFrame:
        """
        回归法合成（滚动 OLS）
        
        使用滚动窗口回归估计因子权重
        """
        pass

    @staticmethod
    def ml_combine(
        factor_data: Dict[str, pd.DataFrame],
        target_returns: pd.DataFrame,
        model_type: str = "lightgbm",
    ) -> pd.DataFrame:
        """
        机器学习合成
        
        使用 LightGBM/XGBoost 等模型学习因子组合
        """
        pass
```

---

### 2.4 组合优化引擎 (Portfolio Optimization Engine)

```python
# backend/app/services/portfolio/optimizer.py

class PortfolioOptimizer:
    """
    组合优化引擎
    
    功能：
    1. 均值 - 方差优化（Markowitz）
    2. Black-Litterman 模型
    3. Risk Parity（风险平价）
    4. Hierarchical Risk Parity (HRP)
    5. 约束优化（行业/个股权重限制）
    """

    @staticmethod
    def mean_variance_optimize(
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        risk_aversion: float = 2.0,
        max_weight: float = 0.1,
        min_weight: float = 0.0,
    ) -> pd.Series:
        """
        均值 - 方差优化
        
        Maximize: w^T * μ - λ/2 * w^T * Σ * w
        Subject to: sum(w) = 1, min_weight <= w <= max_weight
        """
        pass

    @staticmethod
    def black_litterman_optimize(
        market_caps: pd.Series,
        views: List[Dict],  # [{"stocks": [...], "view": 0.05, "confidence": 0.5}]
        risk_aversion: float = 2.5,
        tau: float = 0.05,
    ) -> pd.Series:
        """
        Black-Litterman 模型
        
        结合市场均衡和主观观点
        """
        pass

    @staticmethod
    def risk_parity_optimize(
        covariance_matrix: pd.DataFrame,
        max_weight: float = 0.2,
    ) -> pd.Series:
        """
        风险平价优化
        
        每个资产贡献相同的风险
        """
        pass

    @staticmethod
    def hrp_optimize(
        returns: pd.DataFrame,
    ) -> pd.Series:
        """
        层次风险平价（Hierarchical Risk Parity）
        
        基于聚类树形结构分配权重
        """
        pass

    @staticmethod
    def factor_portfolio_optimize(
        factor_scores: pd.Series,
        sector_neutral: bool = True,
        max_weight: float = 0.05,
        turnover_penalty: float = 0.01,
    ) -> pd.Series:
        """
        因子组合优化
        
        在因子得分基础上加入行业中性、换手控制等约束
        """
        pass
```

---

### 2.5 交易信号引擎 (Trading Signal Engine)

```python
# backend/app/services/signals/signal_engine.py

class SignalEngine:
    """
    交易信号引擎
    
    功能：
    1. 信号生成
    2. 信号过滤
    3. 信号组合
    4. 仓位计算
    """

    @staticmethod
    def generate_signal(
        factor_scores: pd.Series,
        method: str = "top_bottom",
        top_pct: float = 0.2,
        bottom_pct: float = 0.2,
    ) -> pd.Series:
        """
        生成交易信号
        
        Args:
            factor_scores: 因子综合得分
            method: "top_bottom" 或 "continuous"
            top_pct: 做多比例
            bottom_pct: 做空比例
        
        Returns:
            signal: 1 (做多), -1 (做空), 0 (平仓)
        """
        pass

    @staticmethod
    def filter_signal(
        signal: pd.Series,
        liquidity_filter: pd.Series,
       停牌 filter: pd.Series,
        st_filter: pd.Series,
    ) -> pd.Series:
        """
        信号过滤
        
        剔除：ST 股票、停牌股票、流动性不足股票
        """
        pass

    @staticmethod
    def combine_signals(
        signals: Dict[str, pd.Series],
        weights: Dict[str, float],
    ) -> pd.Series:
        """
        信号组合
        
        多个策略信号的加权组合
        """
        pass

    @staticmethod
    def calculate_position_size(
        signal: pd.Series,
        portfolio_value: float,
        max_position_pct: float = 0.1,
        risk_budget: Optional[pd.Series] = None,
    ) -> pd.Series:
        """
        计算仓位大小
        
        Returns:
            每只股票的目标持仓金额
        """
        pass
```

---

### 2.6 风控引擎 (Risk Management Engine)

```python
# backend/app/services/risk/risk_engine.py

class RiskEngine:
    """
    风控引擎
    
    功能：
    1. 实时风险指标计算
    2. 敞口监控
    3. 止损止盈
    4. VaR/CVaR 计算
    """

    @staticmethod
    def calculate_var(
        returns: pd.Series,
        confidence: float = 0.95,
        method: str = "historical",
    ) -> float:
        """
        计算 VaR（Value at Risk）
        
        Args:
            returns: 收益率序列
            confidence: 置信水平
            method: "historical" / "parametric" / "monte_carlo"
        """
        pass

    @staticmethod
    def calculate_cvar(
        returns: pd.Series,
        confidence: float = 0.95,
    ) -> float:
        """计算 CVaR（条件 VaR）"""
        pass

    @staticmethod
    def calculate_exposure(
        positions: pd.Series,
        betas: pd.Series,
    ) -> Dict[str, float]:
        """
        计算风险敞口
        
        Returns:
            {"market_beta": 0.8, "sector_exposure": {...}}
        """
        pass

    @staticmethod
    def check_drawdown_limit(
        current_nav: float,
        peak_nav: float,
        max_drawdown: float = 0.1,
    ) -> bool:
        """
        检查是否触及最大回撤限制
        """
        pass

    @staticmethod
    def generate_stop_loss_orders(
        positions: pd.Series,
        current_prices: pd.Series,
        entry_prices: pd.Series,
        stop_loss_pct: float = 0.1,
    ) -> List[Dict]:
        """
        生成止损订单
        """
        pass
```

---

## 三、数据库设计

### 3.1 核心表结构

```sql
-- 因子定义表
CREATE TABLE factors (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    calculation_params JSONB,
    lookback_period INTEGER,
    decay_period INTEGER,
    ic_mean NUMERIC(8,6),
    ic_ir NUMERIC(8,4),
    annual_return NUMERIC(8,4),
    sharpe_ratio NUMERIC(8,4),
    max_drawdown NUMERIC(8,4),
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- 因子值表（按日期分区）
CREATE TABLE factor_values (
    id VARCHAR PRIMARY KEY,
    factor_id VARCHAR REFERENCES factors(id),
    ticker VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    value NUMERIC(18,8),
    zscore_value NUMERIC(10,4),
    rank_value NUMERIC(6,4),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(factor_id, ticker, trade_date)
);
CREATE INDEX idx_factor_values_ticker_date ON factor_values(ticker, trade_date);
CREATE INDEX idx_factor_values_date ON factor_values(trade_date);

-- 策略定义表
CREATE TABLE quant_strategies (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50),  -- FACTOR_LONG_SHORT / FACTOR_LONG_ONLY / MARKET_NEUTRAL
    factor_weights JSONB,  -- {"factor_1": 0.3, "factor_2": 0.5}
    rebalance_frequency VARCHAR(20),  -- DAILY / WEEKLY / MONTHLY
    max_position_pct NUMERIC(5,2),
    max_sector_exposure NUMERIC(5,2),
    turnover_limit NUMERIC(5,2),
    stop_loss_pct NUMERIC(5,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 策略信号表
CREATE TABLE strategy_signals (
    id VARCHAR PRIMARY KEY,
    strategy_id VARCHAR REFERENCES quant_strategies(id),
    ticker VARCHAR(20) NOT NULL,
    signal_date DATE NOT NULL,
    signal_strength NUMERIC(6,4),  -- -1 to 1
    target_weight NUMERIC(6,4),
    current_price NUMERIC(18,4),
    status VARCHAR(20),  -- PENDING / EXECUTED / CANCELLED
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(strategy_id, ticker, signal_date)
);

-- 因子回测结果表
CREATE TABLE factor_backtest_results (
    id VARCHAR PRIMARY KEY,
    factor_id VARCHAR REFERENCES factors(id),
    backtest_start DATE,
    backtest_end DATE,
    annual_return NUMERIC(8,4),
    sharpe_ratio NUMERIC(8,4),
    max_drawdown NUMERIC(8,4),
    win_rate NUMERIC(6,4),
    ic_mean NUMERIC(8,6),
    icir NUMERIC(8,4),
    turnover_rate NUMERIC(8,4),
    backtest_params JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 组合优化配置表
CREATE TABLE portfolio_optimization_configs (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    optimizer_type VARCHAR(50),  -- MEAN_VARIANCE / BLACK_LITTERMAN / RISK_PARITY / HRP
    risk_aversion NUMERIC(4,2),
    max_weight NUMERIC(5,2),
    min_weight NUMERIC(5,2),
    target_return NUMERIC(6,4),
    target_volatility NUMERIC(6,4),
    sector_constraints JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 四、API 设计

### 4.1 因子管理 API

```python
# backend/app/api/v1/endpoints/quant_factors.py

router = APIRouter(prefix="/quant/factors", tags=["quant-factors"])

@router.get("/factors")
async def list_factors(
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
):
    """获取因子列表"""
    pass

@router.get("/factors/{factor_id}")
async def get_factor_detail(factor_id: str):
    """获取因子详情"""
    pass

@router.post("/factors")
async def create_factor(factor: FactorCreateSchema):
    """创建自定义因子"""
    pass

@router.get("/factors/{factor_id}/ic-analysis")
async def get_factor_ic_analysis(
    factor_id: str,
    start_date: date,
    end_date: date,
):
    """获取因子 IC 分析"""
    pass

@router.get("/factors/{factor_id}/layered-backtest")
async def get_factor_layered_backtest(
    factor_id: str,
    start_date: date,
    end_date: date,
    n_layers: int = 10,
):
    """获取因子分层回测结果"""
    pass

@router.post("/factors/{factor_id}/calculate")
async def calculate_factor_values(
    factor_id: str,
    tickers: List[str],
    dates: Tuple[date, date],
):
    """计算因子值"""
    pass
```

### 4.2 策略回测 API

```python
# backend/app/api/v1/endpoints/quant_backtest.py

router = APIRouter(prefix="/quant/backtest", tags=["quant-backtest"])

@router.post("/run")
async def run_backtest(
    strategy_config: BacktestConfigSchema,
):
    """
    执行策略回测
    
    返回：
    - 权益曲线
    - 绩效指标
    - 交易记录
    - 持仓历史
    """
    pass

@router.get("/results/{result_id}")
async def get_backtest_result(result_id: str):
    """获取回测结果详情"""
    pass

@router.get("/results")
async def list_backtest_results(
    strategy_id: Optional[str] = Query(None),
    limit: int = 20,
):
    """获取回测结果列表"""
    pass

@router.get("/compare")
async def compare_strategies(
    result_ids: List[str] = Query(...),
):
    """对比多个策略表现"""
    pass
```

### 4.3 实盘交易 API

```python
# backend/app/api/v1/endpoints/quant_trading.py

router = APIRouter(prefix="/quant/trading", tags=["quant-trading"])

@router.get("/positions")
async def get_current_positions():
    """获取当前持仓"""
    pass

@router.get("/signals")
async def get_latest_signals(
    strategy_id: Optional[str] = Query(None),
):
    """获取最新交易信号"""
    pass

@router.post("/orders/generate")
async def generate_orders(
    signals: List[SignalSchema],
    current_positions: List[PositionSchema],
):
    """
    根据信号生成订单
    
    考虑：
    - 仓位调整幅度
    - 交易成本
    - 流动性限制
    """
    pass

@router.get("/risk-metrics")
async def get_risk_metrics():
    """获取实时风险指标"""
    pass

@router.post("/rebalance")
async def execute_rebalance(
    strategy_id: str,
):
    """执行调仓"""
    pass
```

---

## 五、实施路线图

### Phase 1: 基础设施 (2-3 周)
- [ ] 因子数据库设计
- [ ] 基础因子实现 (10-15 个)
- [ ] 因子计算引擎
- [ ] IC 分析模块

### Phase 2: 回测系统 (2-3 周)
- [ ] 事件驱动回测框架
- [ ] 因子分层回测
- [ ] 组合回测
- [ ] 绩效分析模块

### Phase 3: 组合优化 (2 周)
- [ ] 均值方差优化
- [ ] Risk Parity
- [ ] 约束优化
- [ ] 行业中性化

### Phase 4: 交易系统 (2-3 周)
- [ ] 信号生成引擎
- [ ] 订单执行模块
- [ ] 风控模块
- [ ] 实盘监控

### Phase 5: 前端界面 (2-3 周)
- [ ] 因子研究 Dashboard
- [ ] 回测结果可视化
- [ ] 实盘监控界面
- [ ] 风险控制面板

---

## 六、技术选型

| 模块 | 技术方案 |
|------|----------|
| 因子计算 | pandas + numpy + numba (加速) |
| 组合优化 | cvxpy + scipy.optimize |
| 机器学习因子 | lightgbm + sklearn |
| 回测引擎 | 自研事件驱动框架 |
| 时序数据库 | PostgreSQL + TimescaleDB |
| 缓存 | Redis (因子值缓存) |
| 任务调度 | Celery + Redis |
| 前端可视化 | ECharts / Recharts |

---

## 七、关键绩效指标

### 因子层面
- IC > 0.04 (4%)
- ICIR > 0.5
- 因子换手率 < 50%/月
- 因子衰减周期 > 5 日

### 组合层面
- 年化收益 > 15%
- 夏普比率 > 1.5
- 最大回撤 < 15%
- 年化换手 < 300%

---

## 八、风险与注意事项

1. **数据质量**：财务数据重述、停牌处理
2. **过拟合风险**：样本外测试、交叉验证
3. **交易成本**：佣金、冲击成本建模
4. **市场 regime 变化**：因子失效监控
5. **流动性风险**：小市值因子容量限制

---

**附录 A: 因子计算公式详见**: `docs/quant_factor_formulas.md`
**附录 B: 回测框架设计详见**: `docs/quant_backtest_design.md`
**附录 C: 风控规则详见**: `docs/quant_risk_rules.md`
