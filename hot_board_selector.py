from typing import List, Dict, Literal
import akshare as ak
import pandas as pd


BoardType = Literal["industry", "concept"]


def safe_float(value, default=0.0) -> float:
    """
    安全转 float，避免 None / '-' / 空字符串 报错
    """
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip()
            if value in ("", "-", "--", "None", "nan"):
                return default
        return float(value)
    except Exception:
        return default


def safe_str(value, default="") -> str:
    if value is None:
        return default
    return str(value).strip()


def normalize_stock_record(row: pd.Series) -> Dict:
    """
    把 AKShare 返回的原始字段，统一转成你自己的标准字段格式
    """
    name = safe_str(row.get("名称", ""))
    return {
        "code": safe_str(row.get("代码", "")),
        "name": name,
        "pct_chg": safe_float(row.get("涨跌幅", 0)),
        "amount": safe_float(row.get("成交额", 0)),
        "turnover": safe_float(row.get("换手率", 0)),
        "is_st": "ST" in name.upper(),
        "is_suspended": False,   # 东方财富这个成份股接口一般不给停牌布尔字段，这里先默认 False
    }


def get_hot_boards(board_type: BoardType = "industry") -> List[Dict]:
    """
    获取所有热门板块（行业 or 概念），并返回统一格式：
    [
        {"name": "机器人", "pct_chg": 4.8, "board_type": "concept"},
        ...
    ]
    """
    if board_type == "industry":
        df = ak.stock_board_industry_name_em()
    elif board_type == "concept":
        df = ak.stock_board_concept_name_em()
    else:
        raise ValueError("board_type 只能是 'industry' 或 'concept'")

    results = []
    for _, row in df.iterrows():
        results.append({
            "name": safe_str(row.get("板块名称", "")),
            "pct_chg": safe_float(row.get("涨跌幅", 0)),
            "board_type": board_type,
        })

    # 按板块涨幅从高到低排
    results.sort(key=lambda x: x["pct_chg"], reverse=True)
    return results


def get_board_stocks(board_name: str, board_type: BoardType = "industry") -> List[Dict]:
    """
    获取某个板块的成份股，并转成统一格式
    """
    if board_type == "industry":
        df = ak.stock_board_industry_cons_em(symbol=board_name)
    elif board_type == "concept":
        df = ak.stock_board_concept_cons_em(symbol=board_name)
    else:
        raise ValueError("board_type 只能是 'industry' 或 'concept'")

    stocks = []
    for _, row in df.iterrows():
        stocks.append(normalize_stock_record(row))

    return stocks


def pick_top_stocks(board_stocks: List[Dict], top_k: int = 3) -> List[Dict]:
    """
    每个板块选 3 只热门股
    逻辑：
    1. 去 ST
    2. 去停牌
    3. 按 涨幅 / 成交额 / 换手率 排序
    """
    filtered = []
    for s in board_stocks:
        if s.get("is_st"):
            continue
        if s.get("is_suspended"):
            continue
        filtered.append(s)

    ranked = sorted(
        filtered,
        key=lambda s: (
            s.get("pct_chg", 0),
            s.get("amount", 0),
            s.get("turnover", 0),
        ),
        reverse=True,
    )
    return ranked[:top_k]


def build_hot_board_report(
    board_type: BoardType = "industry",
    stock_top_k: int = 3,
    board_limit: int | None = None,
) -> List[Dict]:
    """
    核心函数：
    1. 获取全部板块
    2. 板块按涨幅排序
    3. 每个板块取 top_k 只热门股
    4. 返回按板块分组的结果
    """
    hot_boards = get_hot_boards(board_type=board_type)

    if board_limit is not None:
        hot_boards = hot_boards[:board_limit]

    report = []
    for board in hot_boards:
        board_name = board["name"]
        board_stocks = get_board_stocks(board_name, board_type=board_type)
        top_stocks = pick_top_stocks(board_stocks, top_k=stock_top_k)

        report.append({
            "board_name": board_name,
            "board_type": board_type,
            "board_pct_chg": board.get("pct_chg", 0),
            "top_stocks": top_stocks,
        })

    return report


def build_all_boards_report(
    stock_top_k: int = 3,
    include_industry: bool = True,
    include_concept: bool = True,
    industry_limit: int | None = None,
    concept_limit: int | None = None,
) -> List[Dict]:
    """
    同时获取 行业板块 + 概念板块
    """
    final_report = []

    if include_industry:
        final_report.extend(
            build_hot_board_report(
                board_type="industry",
                stock_top_k=stock_top_k,
                board_limit=industry_limit,
            )
        )

    if include_concept:
        final_report.extend(
            build_hot_board_report(
                board_type="concept",
                stock_top_k=stock_top_k,
                board_limit=concept_limit,
            )
        )

    # 全部板块按板块涨幅再排一次
    final_report.sort(key=lambda x: x.get("board_pct_chg", 0), reverse=True)
    return final_report


def format_report_text(report: List[Dict]) -> str:
    """
    输出成清晰文本，方便终端查看、邮件发送、喂给 Gemini
    """
    lines = []
    lines.append("=== A股热门板块分析 ===")

    for idx, board in enumerate(report, start=1):
        lines.append(
            f"\n{idx}. 板块: {board['board_name']} "
            f"| 类型: {board['board_type']} "
            f"| 涨幅: {board['board_pct_chg']:.2f}%"
        )

        if not board["top_stocks"]:
            lines.append("   - 暂无可用成份股数据")
            continue

        for stock in board["top_stocks"]:
            lines.append(
                f"   - {stock['name']}({stock['code']}) "
                f"涨幅:{stock['pct_chg']:.2f}% "
                f"成交额:{stock['amount']:.0f} "
                f"换手率:{stock['turnover']:.2f}%"
            )

    return "\n".join(lines)


if __name__ == "__main__":
    # 方案1：只看行业板块
    # report = build_hot_board_report(board_type="industry", stock_top_k=3)

    # 方案2：只看概念板块
    # report = build_hot_board_report(board_type="concept", stock_top_k=3)

    # 方案3：行业+概念一起看
    report = build_all_boards_report(
        stock_top_k=3,
        include_industry=True,
        include_concept=True,
        industry_limit=None,   # None = 不限制板块数量
        concept_limit=None,    # None = 不限制板块数量
    )

    text = format_report_text(report)
    print(text)
