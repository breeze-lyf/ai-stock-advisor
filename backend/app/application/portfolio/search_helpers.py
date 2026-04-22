from __future__ import annotations
import re


# 国际市场后缀映射表
# 参考：https://help.yahoo.com/kb/quote-format-symbology-finance-sln2310.html
MARKET_SUFFIX_MAP = {
    # 中国市场
    ".SZ": [".SZ"],  # 深交所 A 股/B 股
    ".SH": [".SS"],  # 上交所 A 股/B 股 (Yahoo 使用.SS)
    ".HK": [".HK"],  # 港股

    # 美国市场
    ".US": [""],  # 美股通常无后缀

    # 欧洲市场
    ".ST": [".ST"],  # 斯德哥尔摩证券交易所
    ".CO": [".CO"],  # 哥本哈根证券交易所
    ".PA": [".PA"],  # 巴黎泛欧交易所
    ".MI": [".MI"],  # 米兰证券交易所
    ".MC": [".MC"],  # 马德里证券交易所
    ".DE": [".DE"],  # 德国 XETRA
    ".BE": [".BE"],  # 柏林证券交易所
    ".DU": [".DU"],  # 杜塞尔多夫证券交易所
    ".HA": [".HA"],  # 汉诺威证券交易所
    ".SG": [".SG"],  # 斯图加特证券交易所
    ".MU": [".MU"],  # 慕尼黑证券交易所
    ".BR": [".BR"],  # 布鲁塞尔证券交易所
    ".AS": [".AS"],  # 阿姆斯特丹证券交易所
    ".AT": [".AT"],  # 雅典证券交易所
    ".LS": [".LS"],  # 里斯本证券交易所
    ".IR": [".IR"],  # 爱尔兰证券交易所

    # 英国市场
    ".L": [".L"],  # 伦敦证券交易所

    # 亚洲市场（除中国外）
    ".T": [".T"],  # 东京证券交易所
    ".KS": [".KS"],  # 韩国证券交易所
    ".TW": [".TW"],  # 台湾证券交易所
    ".KL": [".KL"],  # 马来西亚证券交易所
    ".JK": [".JK"],  # 雅加达证券交易所
    ".PS": [".PS"],  # 菲律宾证券交易所
    ".BK": [".BK"],  # 曼谷证券交易所
    ".VN": [".VN"],  # 越南证券交易所

    # 大洋洲市场
    ".AX": [".AX"],  # 澳大利亚证券交易所

    # 加拿大市场
    ".TO": [".TO"],  # 多伦多证券交易所
    ".CN": [".CN"],  # 加拿大证券交易所
    ".V": [".V"],  # 加拿大创业板

    # 南美市场
    ".SA": [".SA"],  # 圣保罗证券交易所

    # 俄罗斯市场
    ".ME": [".ME"],  # 莫斯科证券交易所
}


def build_search_candidates(query: str) -> list[str]:
    """
    构建搜索候选股票代码列表

    Args:
        query: 用户输入的搜索词

    Returns:
        候选股票代码列表，用于尝试匹配不同市场的股票代码格式
    """
    normalized = (query or "").strip().upper()
    if not normalized:
        return []

    candidates: list[str] = []

    def add(value: str) -> None:
        if value and value not in candidates:
            candidates.append(value)

    add(normalized)

    # 处理香港股票代码 (.HK 后缀)
    if normalized.endswith(".HK"):
        code = normalized[:-3]
        if code.isdigit():
            # 港股代码可能是 4 位或 5 位数字
            add(f"{code.zfill(4)}.HK")
            add(f"{code.zfill(5)}.HK")
        return candidates

    # 处理中国 A 股代码 (.SH/.SZ 后缀)
    if normalized.endswith(".SH"):
        # 上交所股票，转换为 Yahoo 使用的.SS 后缀
        add(f"{normalized[:-3]}.SS")
        return candidates

    if normalized.endswith(".SZ"):
        # 深交所股票，保持原样
        return candidates

    # 处理纯数字代码
    if normalized.isdigit():
        if len(normalized) <= 5:
            # 5 位以下数字可能是港股
            add(f"{normalized.zfill(4)}.HK")
            add(f"{normalized.zfill(5)}.HK")
        elif len(normalized) == 6:
            # 6 位数字可能是 A 股
            add(f"{normalized}.SZ")
            add(f"{normalized}.SS")
        return candidates

    # 检查是否已经包含已知的市场后缀
    for suffix in MARKET_SUFFIX_MAP.keys():
        if normalized.endswith(suffix):
            # 已经是完整的股票代码格式
            return candidates

    # 对于没有后缀的代码，尝试添加常见的市场后缀
    # 这有助于搜索欧洲、亚洲等国际市场的股票
    if not any(normalized.endswith(s) for s in MARKET_SUFFIX_MAP.keys()):
        # 纯字母代码可能是美股或其他国际市场
        if re.fullmatch(r"[A-Z]+", normalized):
            # 对于 3 个字母以上的代码，除了作为美股（无后缀）外
            # 还尝试添加主要的欧洲市场后缀，以便搜索到国际市场的股票
            if len(normalized) >= 4:
                # 为较长的字母代码添加欧洲市场后缀候选
                # 这些市场可能使用相同的代码但后缀不同
                for suffix in [".ST", ".CO", ".PA", ".MI", ".MC", ".DE", ".L", ".AX", ".TO"]:
                    add(f"{normalized}{suffix}")
        elif len(normalized) >= 3:
            # 对于字母 + 数字组合或其他格式的代码
            # 添加主要的欧洲市场后缀
            for suffix in [".ST", ".CO", ".PA", ".MI", ".MC", ".DE", ".L"]:
                add(f"{normalized}{suffix}")

    return candidates


def infer_search_market_hint(query: str) -> str:
    raw = (query or "").strip()
    normalized = raw.upper()
    if not normalized:
        return "UNKNOWN"

    if re.search(r"[\u4e00-\u9fff]", raw):
        return "CN_TEXT"

    if normalized.endswith((".SZ", ".SS", ".SH", ".HK")):
        return "CN_CODE"

    if normalized.isdigit() and len(normalized) == 6:
        return "CN_CODE"

    if normalized.isdigit() and len(normalized) <= 5:
        return "HK_CODE"

    if re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", normalized):
        return "US_CODE"

    if re.search(r"[A-Z]", normalized):
        return "US_TEXT"

    return "UNKNOWN"


def build_provider_order(preferred_source: str | None, query: str | None = None) -> list[str]:
    hint = infer_search_market_hint(query or "")
    if hint in {"CN_TEXT", "CN_CODE", "HK_CODE"}:
        return ["AKSHARE", "YFINANCE"]
    if hint in {"US_TEXT", "US_CODE"}:
        return ["YFINANCE", "AKSHARE"]

    preferred = (preferred_source or "AKSHARE").upper()
    if preferred == "YFINANCE":
        return ["YFINANCE", "AKSHARE"]
    return ["AKSHARE", "YFINANCE"]
