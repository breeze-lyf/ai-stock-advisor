import pandas as pd
import numpy as np
import pytest
from app.services.indicators import TechnicalIndicators

@pytest.fixture
def sample_data():
    """生成 60 天的模拟 K 线数据 (Generate 60 days of mock OHLCV data)"""
    dates = pd.date_range(start="2024-01-01", periods=60)
    data = {
        'Open': np.random.uniform(100, 110, 60),
        'High': np.random.uniform(110, 120, 60),
        'Low': np.random.uniform(90, 100, 60),
        'Close': np.random.uniform(100, 110, 60),
        'Volume': np.random.uniform(1000000, 2000000, 60)
    }
    return pd.DataFrame(data, index=dates)

def test_add_historical_indicators(sample_data):
    """测试批量添加指标 (Test batch adding indicators)"""
    df = TechnicalIndicators.add_historical_indicators(sample_data)
    
    # 验证关键列是否存在
    expected_cols = ['macd', 'macd_signal', 'macd_hist', 'rsi', 'bb_upper', 'bb_middle', 'bb_lower']
    for col in expected_cols:
        assert col in df.columns
        # 验证是否有数据（排除前几个 NaN）
        assert not df[col].tail(10).isna().any()

def test_calculate_all(sample_data):
    """测试全量指标计算快照 (Test comprehensive indicator snapshot)"""
    result = TechnicalIndicators.calculate_all(sample_data)
    
    # 验证返回字典的键及其值类型
    assert isinstance(result, dict)
    assert "macd_val" in result
    assert "rsi_14" in result
    assert "bb_upper" in result
    assert "risk_reward_ratio" in result
    
    # 验证具体的逻辑：RSI 应该在 0-100 之间
    assert 0 <= result["rsi_14"] <= 100
    
    # 验证阻力位必须高于支撑位
    if "resistance_1" in result and "support_1" in result:
        assert result["resistance_1"] > result["support_1"]

def test_empty_data():
    """测试空数据处理 (Test empty data handling)"""
    df_empty = pd.DataFrame()
    
    # 不应崩溃，应返回原样或空字典
    res_df = TechnicalIndicators.add_historical_indicators(df_empty)
    assert res_df.empty
    
    res_dict = TechnicalIndicators.calculate_all(df_empty)
    assert res_dict == {}

def test_insufficient_data():
    """测试数据量不足的情况 (Test insufficient data)"""
    dates = pd.date_range(start="2024-01-01", periods=5)
    data = {
        'Open': [100]*5, 'High': [110]*5, 'Low': [90]*5, 'Close': [100]*5, 'Volume': [1000]*5
    }
    df_small = pd.DataFrame(data, index=dates)
    
    # 数据量不足以计算大部分指标，应优雅返回
    res_dict = TechnicalIndicators.calculate_all(df_small)
    assert res_dict == {}
