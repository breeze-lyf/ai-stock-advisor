# 技术指标量化引擎 (Technical Indicators Quantitative Engine)
# 职责：这是本系统的“数学大脑”。
# 它把原始的一串价格数字，转化成股民常用的 MACD、RSI、布林带等指标。
# 这些计算结果会被存入数据库，并作为上下文喂给 AI。

import pandas as pd

class TechnicalIndicators:
    @staticmethod
    def add_historical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        批量添加历史指标：专门为 K 线图（Chart）准备数据。
        当你打开股票详情页看到的那些波动曲线，就是这里算出来的。
        """
        if df.empty or len(df) < 10:
            return df
            
        df = df.copy()
        close_prices = df['Close']
        
        # 1. MACD (指数平滑异同平均线)
        # 逻辑：通过快线(12日)和慢线(26日)的差值，判断股价的爆发力和动能。
        ema12 = close_prices.ewm(span=12, adjust=False).mean()
        ema26 = close_prices.ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 2. RSI (14) - 相对强弱指数
        # 逻辑：衡量过去 14 天买方和卖方谁更强。
        # 超过 70 通常代表“太热了/超买”，低于 30 代表“太冷了/超卖”。
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 3. Bollinger Bands (20) - 布林带
        # 逻辑：给股价装上“护栏”。
        # 股价大多在上下轨之间运行，触碰下轨往往有支撑，触碰上轨往往有压力。
        ma20 = close_prices.rolling(window=20).mean()
        std20 = close_prices.rolling(window=20).std()
        df['bb_upper'] = ma20 + (std20 * 2)
        df['bb_middle'] = ma20
        df['bb_lower'] = ma20 - (std20 * 2)
        
        return df

    @staticmethod
    def calculate_all(hist: pd.DataFrame) -> dict:
        """
        全量指标快照：只提取“最新那一天”的数值。
        AI 在进行诊断时，需要知道昨晚收盘时的 RSI 是多少。
        """
        if hist.empty or len(hist) < 10:
            return {}
            
        close_prices = hist['Close']
        high_prices = hist['High']
        low_prices = hist['Low']
        volumes = hist['Volume']
        result = {}

        # 1. 计算最新的 MACD 点位和金叉/死叉状态
        ema12 = close_prices.ewm(span=12, adjust=False).mean()
        ema26 = close_prices.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line
        
        result["macd_val"] = float(macd_line.iloc[-1])
        result["macd_signal"] = float(signal_line.iloc[-1])
        result["macd_hist"] = float(macd_hist.iloc[-1])
        
        curr_macd = float(macd_line.iloc[-1])
        curr_signal = float(signal_line.iloc[-1])
        # 判断金叉 (快线上穿慢线)
        result["macd_cross"] = "GOLDEN" if curr_macd >= curr_signal else "DEATH"
        
        # 2. MA (移动平均线) & 量比
        if len(close_prices) >= 20:
            ma20 = close_prices.rolling(window=20).mean()
            result["ma_20"] = float(ma20.iloc[-1])
            # 量比：当前成交量与过去 20 天均量的比值（判断是否有大资金入场）
            ma20_vol = volumes.rolling(window=20).mean()
            result["volume_ma_20"] = float(ma20_vol.iloc[-1])
            result["volume_ratio"] = float(volumes.iloc[-1] / ma20_vol.iloc[-1]) if float(ma20_vol.iloc[-1]) > 0 else 0

        # 3. KDJ (随机指标) - 用于捕捉超短期的买卖点
        if len(close_prices) >= 9:
            low_9 = low_prices.rolling(window=9).min()
            high_9 = high_prices.rolling(window=9).max()
            rsv = (close_prices - low_9) / (high_9 - low_9) * 100
            k = rsv.ewm(com=2, adjust=False).mean()
            d = k.ewm(com=2, adjust=False).mean()
            j = 3 * k - 2 * d
            result["k_line"] = float(k.iloc[-1])
            result["d_line"] = float(d.iloc[-1])
            result["j_line"] = float(j.iloc[-1])

        # 4. 关键压力/支撑位 (Pivot Points)
        # 逻辑：基于昨天的最高、最低、收盘价，预判今天的阻力位。
        if len(close_prices) >= 2:
            last_h, last_l, last_c = high_prices.iloc[-2], low_prices.iloc[-2], close_prices.iloc[-2]
            pivot = (last_h + last_l + last_c) / 3
            result["pivot_point"] = float(pivot)
            result["resistance_1"] = float(2 * pivot - last_l) # 第一阻力
            result["support_1"] = float(2 * pivot - last_h)    # 第一支撑

        # 5. 【核心逻辑】盈亏比的机器估算
        # 逻辑：如果现在买，潜在空间(到阻力位)是不是潜在风险(到支撑位)的 1.5 倍以上？
        curr_p = float(close_prices.iloc[-1])
        r1, s1 = result.get("resistance_1"), result.get("support_1")
        
        calculated_rr = None
        if r1 and s1 and r1 > curr_p > s1:
            risk, reward = curr_p - s1, r1 - curr_p
            if risk > 0.01:
                calculated_rr = reward / risk

        if calculated_rr is not None:
            result["risk_reward_ratio"] = round(float(calculated_rr), 2)

        return result
