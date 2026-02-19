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
        量化指标全量计算：计算最新快照所需的全部技术指标。
        这些指标是本系统的“底层眼睛”，支撑起前端仪表盘并作为 AI 诊断的精确上下文。
        """
        if hist.empty or len(hist) < 10:
            return {}
            
        close_prices = hist['Close']
        high_prices = hist['High']
        low_prices = hist['Low']
        volumes = hist['Volume']
        result = {}

        # 1. MACD (趋势动能)
        ema12 = close_prices.ewm(span=12, adjust=False).mean()
        ema26 = close_prices.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line
        
        result["macd_val"] = float(macd_line.iloc[-1])
        result["macd_signal"] = float(signal_line.iloc[-1])
        result["macd_hist"] = float(macd_hist.iloc[-1])
        result["macd_cross"] = "GOLDEN" if macd_line.iloc[-1] >= signal_line.iloc[-1] else "DEATH"
        if len(macd_hist) >= 2:
            result["macd_hist_slope"] = float(macd_hist.iloc[-1] - macd_hist.iloc[-2])

        # 2. RSI (14) - 相对强弱指数
        if len(close_prices) >= 15:
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-9)
            rsi = 100 - (100 / (1 + rs))
            result["rsi_14"] = float(rsi.iloc[-1])

        # 3. 移动平均线 (MA 20/50/200) & 量比
        result["ma_20"] = float(close_prices.rolling(window=20).mean().iloc[-1]) if len(close_prices) >= 20 else None
        result["ma_50"] = float(close_prices.rolling(window=50).mean().iloc[-1]) if len(close_prices) >= 50 else None
        result["ma_200"] = float(close_prices.rolling(window=200).mean().iloc[-1]) if len(close_prices) >= 200 else None

        if len(volumes) >= 20:
            ma20_vol = volumes.rolling(window=20).mean()
            result["volume_ma_20"] = float(ma20_vol.iloc[-1])
            result["volume_ratio"] = float(volumes.iloc[-1] / ma20_vol.iloc[-1]) if ma20_vol.iloc[-1] > 0 else 0

        # 4. 布林带 (Bollinger Bands)
        if len(close_prices) >= 20:
            ma20 = close_prices.rolling(window=20).mean()
            std20 = close_prices.rolling(window=20).std()
            result["bb_upper"] = float((ma20 + (std20 * 2)).iloc[-1])
            result["bb_middle"] = float(ma20.iloc[-1])
            result["bb_lower"] = float((ma20 - (std20 * 2)).iloc[-1])

        # 5. Volatility (ATR 14) - 平均真实波幅
        if len(hist) >= 15:
            high_low = high_prices - low_prices
            high_close = (high_prices - close_prices.shift()).abs()
            low_close = (low_prices - close_prices.shift()).abs()
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=14).mean()
            result["atr_14"] = float(atr.iloc[-1])

        # 6. KDJ (随机指标)
        if len(close_prices) >= 9:
            low_9 = low_prices.rolling(window=9).min()
            high_9 = high_prices.rolling(window=9).max()
            denom = high_9 - low_9
            rsv = (close_prices - low_9) / (denom + 1e-9) * 100
            k = rsv.ewm(com=2, adjust=False).mean()
            d = k.ewm(com=2, adjust=False).mean()
            j = 3 * k - 2 * d
            result["k_line"] = float(k.iloc[-1])
            result["d_line"] = float(d.iloc[-1])
            result["j_line"] = float(j.iloc[-1])

        # 7. 关键压力/支撑位 (Pivot Points)
        if len(close_prices) >= 2:
            last_h, last_l, last_c = high_prices.iloc[-2], low_prices.iloc[-2], close_prices.iloc[-2]
            pivot = (last_h + last_l + last_c) / 3
            result["pivot_point"] = float(pivot)
            result["resistance_1"] = float(2 * pivot - last_l)
            result["support_1"] = float(2 * pivot - last_h)
            result["resistance_2"] = float(pivot + (last_h - last_l))
            result["support_2"] = float(pivot - (last_h - last_l))

        # 8. 盈亏比的机器估算
        curr_p = float(close_prices.iloc[-1])
        r1, s1 = result.get("resistance_1"), result.get("support_1")
        if r1 and s1 and r1 > curr_p > s1:
            risk, reward = curr_p - s1, r1 - curr_p
            if risk > 0.01:
                result["risk_reward_ratio"] = round(float(reward / risk), 2)

        return result
