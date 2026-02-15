# 技术指标量化引擎 (Technical Indicators Quantitative Engine)
# 职责：提供基于 Pandas 的高效技术指标计算，支持 K 线渲染和 AI 分析
# 注意：由于 Python 3.14 暂不支持 pandas-ta 的依赖库 numba，当前采用手动实现以保证环境兼容性。
import pandas as pd
import numpy as np

class TechnicalIndicators:
    @staticmethod
    def add_historical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        为 Time-series 图表批量添加指标列 (Batch add indicators for charting)
        - 输入: 包含 Open, High, Low, Close, Volume 的 DataFrame
        - 输出: 增加 MACD, RSI, Bollinger Bands 列的新 DataFrame
        """
        if df.empty or len(df) < 10:
            return df
            
        df = df.copy()
        close_prices = df['Close']
        
        # 1. MACD (指数平滑异同平均线)
        ema12 = close_prices.ewm(span=12, adjust=False).mean()
        ema26 = close_prices.ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 2. RSI (14) - 相对强弱指数
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 3. Bollinger Bands (20) - 布林带
        ma20 = close_prices.rolling(window=20).mean()
        std20 = close_prices.rolling(window=20).std()
        df['bb_upper'] = ma20 + (std20 * 2)
        df['bb_middle'] = ma20
        df['bb_lower'] = ma20 - (std20 * 2)
        
        return df

    @staticmethod
    def calculate_all(hist: pd.DataFrame) -> dict:
        """
        计算全量技术面指标快照 (Calculate comprehensive indicator snapshot)
        - 职责：提取历史 K 线末端的数值，供数据库缓存和 AI 分析 Prompt 使用
        """
        if hist.empty or len(hist) < 10:
            return {}
            
        close_prices = hist['Close']
        high_prices = hist['High']
        low_prices = hist['Low']
        volumes = hist['Volume']
        result = {}

        # 1. MACD 及 柱状图斜率
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
        result["macd_cross"] = "GOLDEN" if curr_macd >= curr_signal else "DEATH"
        
        if len(macd_line) >= 2:
            prev_macd = float(macd_line.iloc[-2])
            prev_signal = float(signal_line.iloc[-2])
            is_new = (prev_macd < prev_signal and curr_macd >= curr_signal) or \
                     (prev_macd > prev_signal and curr_macd <= curr_signal)
            result["macd_is_new_cross"] = is_new
        else:
            result["macd_is_new_cross"] = False

        if len(macd_hist) >= 2:
            result["macd_hist_slope"] = float(macd_hist.iloc[-1] - macd_hist.iloc[-2])
        else:
            result["macd_hist_slope"] = 0.0

        # 2. MA & Volume Ratio
        if len(close_prices) >= 20:
            ma20 = close_prices.rolling(window=20).mean()
            std20 = close_prices.rolling(window=20).std()
            result["ma_20"] = float(ma20.iloc[-1])
            result["bb_upper"] = float(ma20.iloc[-1] + (std20.iloc[-1] * 2))
            result["bb_middle"] = float(ma20.iloc[-1])
            result["bb_lower"] = float(ma20.iloc[-1] - (std20.iloc[-1] * 2))
            
            ma20_vol = volumes.rolling(window=20).mean()
            result["volume_ma_20"] = float(ma20_vol.iloc[-1])
            result["volume_ratio"] = float(volumes.iloc[-1] / ma20_vol.iloc[-1]) if float(ma20_vol.iloc[-1]) > 0 else 0

        # 3. RSI (14)
        if len(close_prices) >= 15:
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            result["rsi_14"] = float(rsi.iloc[-1])

        # 4. KDJ (9, 3, 3)
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

        # 5. ATR (14)
        if len(close_prices) >= 15:
            prev_close = close_prices.shift(1)
            tr = pd.concat([
                high_prices - low_prices,
                (high_prices - prev_close).abs(),
                (low_prices - prev_close).abs()
            ], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean()
            result["atr_14"] = float(atr.iloc[-1])

        # 6. ADX (14)
        if len(close_prices) >= 28:
            up_move = high_prices.diff()
            down_move = low_prices.diff()
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            tr = pd.concat([
                high_prices - low_prices,
                (high_prices - close_prices.shift(1)).abs(),
                (low_prices - close_prices.shift(1)).abs()
            ], axis=1).max(axis=1)
            tr_smooth = tr.rolling(window=14).mean()
            plus_dm_smooth = pd.Series(plus_dm).rolling(window=14).mean()
            minus_dm_smooth = pd.Series(minus_dm).rolling(window=14).mean()
            plus_di = 100 * (plus_dm_smooth / tr_smooth)
            minus_di = 100 * (minus_dm_smooth / tr_smooth)
            dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
            adx = dx.rolling(window=14).mean()
            result["adx_14"] = float(adx.iloc[-1])

        # 7. 枢轴参考点
        if len(close_prices) >= 2:
            last_h = high_prices.iloc[-2]
            last_l = low_prices.iloc[-2]
            last_c = close_prices.iloc[-2]
            pivot = (last_h + last_l + last_c) / 3
            result["pivot_point"] = float(pivot)
            result["resistance_1"] = float(2 * pivot - last_l)
            result["support_1"] = float(2 * pivot - last_h)
            result["resistance_2"] = float(pivot + (last_h - last_l))
            result["support_2"] = float(pivot - (last_h - last_l))

        # 8. MA 长期均线
        if len(close_prices) >= 50:
            result["ma_50"] = float(close_prices.rolling(window=50).mean().iloc[-1])
        if len(close_prices) >= 120:
            result["ma_200"] = float(close_prices.rolling(window=min(len(close_prices), 200)).mean().iloc[-1])

        # 9. 盈亏比自动计算
        curr_p = float(close_prices.iloc[-1])
        r1 = result.get("resistance_1")
        s1 = result.get("support_1")
        if r1 and s1 and r1 > curr_p > s1:
            risk = curr_p - s1
            reward = r1 - curr_p
            if risk > 0: result["risk_reward_ratio"] = round(float(reward / risk), 2)
        elif result.get("bb_upper") and result.get("bb_lower"):
            bb_up, bb_low = result["bb_upper"], result["bb_lower"]
            if bb_up > curr_p > bb_low:
                risk, reward = curr_p - bb_low, bb_up - curr_p
                if risk > 0: result["risk_reward_ratio"] = round(float(reward / risk), 2)
        elif result.get("ma_50") and result.get("atr_14"):
            ma50, atr = result["ma_50"], result["atr_14"]
            upper_target, lower_stop = ma50 + 2 * atr, ma50 - 2 * atr
            if upper_target > curr_p > lower_stop:
                risk, reward = curr_p - lower_stop, upper_target - curr_p
                if risk > 0: result["risk_reward_ratio"] = round(float(reward / risk), 2)

        return result
