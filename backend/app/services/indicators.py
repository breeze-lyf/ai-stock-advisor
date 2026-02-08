import pandas as pd
import numpy as np

class TechnicalIndicators:
    @staticmethod
    def calculate_all(hist: pd.DataFrame) -> dict:
        """
        Calculate all technical indicators from historical data.
        Returns a dict of indicators.
        """
        if hist.empty or len(hist) < 26:
            return {}
            
        close_prices = hist['Close']
        high_prices = hist['High']
        low_prices = hist['Low']
        volumes = hist['Volume']
        result = {}

        # 1. MACD (12, 26, 9)
        ema12 = close_prices.ewm(span=12, adjust=False).mean()
        ema26 = close_prices.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line
        
        result["macd_val"] = float(macd_line.iloc[-1])
        result["macd_signal"] = float(signal_line.iloc[-1])
        result["macd_hist"] = float(macd_hist.iloc[-1])
        
        # MACD Slope (一阶导数)
        if len(macd_hist) >= 2:
            result["macd_hist_slope"] = float(macd_hist.iloc[-1] - macd_hist.iloc[-2])
        else:
            result["macd_hist_slope"] = 0.0

        # 2. MA & Bollinger Bands
        if len(close_prices) >= 20:
            ma20 = close_prices.rolling(window=20).mean()
            std20 = close_prices.rolling(window=20).std()
            result["ma_20"] = float(ma20.iloc[-1])
            result["bb_upper"] = float(ma20.iloc[-1] + (std20.iloc[-1] * 2))
            result["bb_middle"] = float(ma20.iloc[-1])
            result["bb_lower"] = float(ma20.iloc[-1] - (std20.iloc[-1] * 2))
            
            # Volume MA20 & Ratio
            ma20_vol = volumes.rolling(window=20).mean()
            result["volume_ma_20"] = float(ma20_vol.iloc[-1])
            result["volume_ratio"] = float(volumes.iloc[-1] / ma20_vol.iloc[-1]) if ma20_vol.iloc[-1] > 0 else 0

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

        # 6. ADX (Average Directional Index - 14)
        if len(close_prices) >= 28: # ADX needs more data for smoothing
            up_move = high_prices.diff()
            down_move = low_prices.diff()
            
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            
            # TR calculation (reuse part of ATR logic if needed but self-contained here)
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

        # 7. Support & Resistance (Pivot Points - Classic)
        if len(close_prices) >= 2:
            # Using yesterday's HLC for today's pivots
            last_h = high_prices.iloc[-2]
            last_l = low_prices.iloc[-2]
            last_c = close_prices.iloc[-2]
            
            pivot = (last_h + last_l + last_c) / 3
            result["pivot_point"] = float(pivot)
            result["resistance_1"] = float(2 * pivot - last_l)
            result["support_1"] = float(2 * pivot - last_h)
            result["resistance_2"] = float(pivot + (last_h - last_l))
            result["support_2"] = float(pivot - (last_h - last_l))

        # 8. MA 50 & 200
        if len(close_prices) >= 50:
            result["ma_50"] = float(close_prices.rolling(window=50).mean().iloc[-1])
        if len(close_prices) >= 120: # Use available data up to 200
            result["ma_200"] = float(close_prices.rolling(window=min(len(close_prices), 200)).mean().iloc[-1])

        return result
