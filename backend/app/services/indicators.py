# 技术指标量化引擎 (Technical Indicators Quantitative Engine)
# 职责：提供基于 Pandas 的高效技术指标计算，支持 K 线渲染和 AI 分析
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
        # 算法：12日EMA - 26日EMA，再对差值取9日平滑
        ema12 = close_prices.ewm(span=12, adjust=False).mean()
        ema26 = close_prices.ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 2. RSI (14) - 相对强弱指数
        # 算法：统计 14 周期内收盘涨幅与跌幅的比率
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 3. Bollinger Bands (20) - 布林带
        # 算法：20日中轨 (MA) ± 2倍标准差
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

        # 1. MACD 及 柱状图斜率 (MACD & Histogram Slope)
        # 斜率用于判断动能变化速度（一阶导数）
        ema12 = close_prices.ewm(span=12, adjust=False).mean()
        ema26 = close_prices.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line
        
        result["macd_val"] = float(macd_line.iloc[-1])
        result["macd_signal"] = float(signal_line.iloc[-1])
        result["macd_hist"] = float(macd_hist.iloc[-1])
        
        # MACD 交叉检测与格局判定 (Cross & Regime Detection)
        curr_macd = float(macd_line.iloc[-1])
        curr_signal = float(signal_line.iloc[-1])
        
        # 只要快线在慢线上方，即为金叉格局；反之为死叉格局 (Persistent regime)
        result["macd_cross"] = "GOLDEN" if curr_macd >= curr_signal else "DEATH"
        
        # 判定是否为“新交叉” (Is this a newly formed cross?)
        if len(macd_line) >= 2:
            prev_macd = float(macd_line.iloc[-2])
            prev_signal = float(signal_line.iloc[-2])
            # 如果上一个周期和当前周期的强弱关系发生了反转，则是新交叉
            is_new = (prev_macd < prev_signal and curr_macd >= curr_signal) or \
                     (prev_macd > prev_signal and curr_macd <= curr_signal)
            result["macd_is_new_cross"] = is_new
        else:
            result["macd_is_new_cross"] = False

        if len(macd_hist) >= 2:
            result["macd_hist_slope"] = float(macd_hist.iloc[-1] - macd_hist.iloc[-2])
        else:
            result["macd_hist_slope"] = 0.0

        # 2. MA 均线与成交量比例 (MA & Volume Ratio)
        # 用当前成交量对比 20 日均量，判断缩量或放量
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

        # 3. RSI (14) - 相对强弱
        if len(close_prices) >= 15:
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            result["rsi_14"] = float(rsi.iloc[-1])

        # 4. KDJ (9, 3, 3) - 随机指标
        # 衡量价格处于 9 周期内最高/最低水平的相对位置
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

        # 5. ATR (14) - 平均真实波幅
        # 用于衡量波动性，指导止损位设置
        if len(close_prices) >= 15:
            prev_close = close_prices.shift(1)
            tr = pd.concat([
                high_prices - low_prices,
                (high_prices - prev_close).abs(),
                (low_prices - prev_close).abs()
            ], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean()
            result["atr_14"] = float(atr.iloc[-1])

        # 6. ADX (14) - 平均趋向指数
        # 算法：通过对比连续周期内多空方的趋向变动，判断趋势显著性（非方向）
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

        # 7. 枢轴参考点 (Pivot Points - Classic)
        # 提供前一交易日高低收计算出的阻力/支撑区间
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

        # 8. MA 长期均线 (MA 50 & 200)
        # 用于判定长线牛熊分界线
        if len(close_prices) >= 50:
            result["ma_50"] = float(close_prices.rolling(window=50).mean().iloc[-1])
        if len(close_prices) >= 120:
            result["ma_200"] = float(close_prices.rolling(window=min(len(close_prices), 200)).mean().iloc[-1])

        # 9. 盈亏比自动计算 (Risk/Reward Ratio)
        # 多级回退策略 (Multi-Level Fallback)：
        #   Level 1: 经典枢轴位 Pivot S1/R1
        #   Level 2: 布林带上下轨 BB Upper/Lower
        #   Level 3: MA50 ± 2*ATR (趋势通道)
        # 盈亏比 = (目标收益 Target-Price) / (潜在风险 Price-Stop)
        curr_p = float(close_prices.iloc[-1])
        
        # Level 1: Pivot Points
        r1 = result.get("resistance_1")
        s1 = result.get("support_1")
        
        if r1 and s1 and r1 > curr_p > s1:
            risk = curr_p - s1
            reward = r1 - curr_p
            if risk > 0:
                result["risk_reward_ratio"] = round(float(reward / risk), 2)
            else:
                result["risk_reward_ratio"] = None
        # Level 2: Bollinger Bands
        elif result.get("bb_upper") and result.get("bb_lower"):
            bb_up = result["bb_upper"]
            bb_low = result["bb_lower"]
            if bb_up > curr_p > bb_low:
                risk = curr_p - bb_low
                reward = bb_up - curr_p
                if risk > 0:
                    result["risk_reward_ratio"] = round(float(reward / risk), 2)
                else:
                    result["risk_reward_ratio"] = None
            else:
                result["risk_reward_ratio"] = None
        # Level 3: MA50 ± 2*ATR
        elif result.get("ma_50") and result.get("atr_14"):
            ma50 = result["ma_50"]
            atr = result["atr_14"]
            upper_target = ma50 + 2 * atr
            lower_stop = ma50 - 2 * atr
            if upper_target > curr_p > lower_stop:
                risk = curr_p - lower_stop
                reward = upper_target - curr_p
                if risk > 0:
                    result["risk_reward_ratio"] = round(float(reward / risk), 2)
                else:
                    result["risk_reward_ratio"] = None
            else:
                result["risk_reward_ratio"] = None
        else:
            result["risk_reward_ratio"] = None

        return result
