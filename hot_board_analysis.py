from typing import List, Dict, Literal, Callable
import time
import logging
import akshare as ak
import pandas as pd


logger = logging.getLogger(__name__)

BoardType = Literal["industry", "concept"]

DEFAULT_TOP_K = 3
DEFAULT_INDUSTRY_LIMIT = 10
DEFAULT_CONCEPT_LIMIT = 10


def safe_float(value, default=0.0) -> float:
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


def fetch_with_retry(
    func: Callable,
    *args,
    retries: int = 5,
    sleep_seconds: float = 2.0,
    **kwargs,
):
    """
    通用重试包装：
    - 用于 AKShare 请求不稳定、连接被远端断开时
    - 最多重试 retries 次
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            logger.warning(f"[热点板块] 第 {attempt}/{retries} 次请求失败: {e}")
            if attempt < retries:
                time.sleep(sleep_seconds)
            else:
                raise last_error


def normalize_stock_record(row: pd.Series) -> Dict:
    """
    把 AKShare 返回的原始字段统一转为标准格式
    """
    name = safe_str(row.get("名称", ""))
    latest_price = safe_float(row.get("最新价", 0))

    return {
        "code": safe_str(row.get("代码", "")),
        "name": name,
        "pct_chg": safe_float(row.get("涨跌幅", 0)),
        "amount": safe_float(row.get("成交额", 0)),
        "turnover": safe_float(row.get("换手率", 0)),
        "latest_price": latest_price,
        "is_st": "ST" in name.upper(),
        # 没有明确停牌布尔字段时，做弱判断
        "is_suspended": latest_price == 0 and safe_float(row.get("涨跌幅", 0)) == 0,
    }


def get_hot_boards(board_type: BoardType = "industry") -> List[Dict]:
    """
    获取板块列表（行业 or 概念），按涨跌幅排序
    """
    if board_type == "industry":
        df = fetch_with_retry(ak.stock_board_industry_name_em)
    elif board_type == "concept":
        df = fetch_with_retry(ak.stock_board_concept_name_em)
    else:
        raise ValueError("board_type 只能是 'industry' 或 'concept'")

    results = []
    for _, row in df.iterrows():
        board_name = safe_str(row.get("板块名称", ""))
        if not board_name:
            continue

        results.append({
            "name": board_name,
            "pct_chg": safe_float(row.get("涨跌幅", 0)),
            "board_type": board_type,
        })

    results.sort(key=lambda x: x["pct_chg"], reverse=True)
    return results


def get_board_stocks(board_name: str, board_type: BoardType = "industry") -> List[Dict]:
    """
    获取某个板块的成份股
    """
    if board_type == "industry":
        df = fetch_with_retry(ak.stock_board_industry_cons_em, symbol=board_name)
    elif board_type == "concept":
        df = fetch_with_retry(ak.stock_board_concept_cons_em, symbol=board_name)
    else:
        raise ValueError("board_type 只能是 'industry' 或 'concept'")

    stocks = []
    for _, row in df.iterrows():
        stocks.append(normalize_stock_record(row))

    return stocks


def pick_top_stocks(board_stocks: List[Dict], top_k: int = 3) -> List[Dict]:
    """
    每个板块选 3 只热门股
    规则：
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
    stock_top_k: int = DEFAULT_TOP_K,
    board_limit: int | None = None,
) -> List[Dict]:
    """
    获取某一类板块（行业/概念）的热点报告
    """
    hot_boards = get_hot_boards(board_type=board_type)

    if board_limit is not None:
        hot_boards = hot_boards[:board_limit]

    report = []
    for board in hot_boards:
        board_name = board["name"]
        error_message = ""

        try:
            board_stocks = get_board_stocks(board_name, board_type=board_type)
            top_stocks = pick_top_stocks(board_stocks, top_k=stock_top_k)
        except Exception as e:
            logger.warning(f"[热点板块] 获取板块 {board_name} 成分股失败: {e}")
            top_stocks = []
            error_message = str(e)

        report.append({
            "board_name": board_name,
            "board_type": board_type,
            "board_pct_chg": board.get("pct_chg", 0),
            "top_stocks": top_stocks,
            "error": error_message,
        })

        # 降低请求频率
        time.sleep(1)

    return report


def build_all_boards_report(
    stock_top_k: int = DEFAULT_TOP_K,
    include_industry: bool = True,
    include_concept: bool = True,
    industry_limit: int | None = DEFAULT_INDUSTRY_LIMIT,
    concept_limit: int | None = DEFAULT_CONCEPT_LIMIT,
) -> List[Dict]:
    """
    同时获取 行业板块 + 概念板块
    """
    final_report = []

    if include_industry:
        try:
            final_report.extend(
                build_hot_board_report(
                    board_type="industry",
                    stock_top_k=stock_top_k,
                    board_limit=industry_limit,
                )
            )
        except Exception as e:
            logger.warning(f"[热点板块] 获取行业板块列表失败: {e}")
            final_report.append({
                "board_name": "行业板块列表获取失败",
                "board_type": "industry",
                "board_pct_chg": 0,
                "top_stocks": [],
                "error": str(e),
            })

    if include_concept:
        try:
            final_report.extend(
                build_hot_board_report(
                    board_type="concept",
                    stock_top_k=stock_top_k,
                    board_limit=concept_limit,
                )
            )
        except Exception as e:
            logger.warning(f"[热点板块] 获取概念板块列表失败: {e}")
            final_report.append({
                "board_name": "概念板块列表获取失败",
                "board_type": "concept",
                "board_pct_chg": 0,
                "top_stocks": [],
                "error": str(e),
            })

    return final_report


def _format_single_section(title: str, boards: List[Dict]) -> List[str]:
    lines = [f"## {title}"]

    if not boards:
        lines.append("- 暂无数据")
        return lines

    for idx, board in enumerate(boards, start=1):
        lines.append(
            f"{idx}. {board['board_name']} | 涨幅: {board['board_pct_chg']:.2f}%"
        )

        if board.get("error"):
            lines.append(f"   - 成分股获取失败: {board['error']}")
            continue

        top_stocks = board.get("top_stocks", [])
        if not top_stocks:
            lines.append("   - 暂无可用成份股")
            continue

        for stock in top_stocks[:3]:
            lines.append(
                f"   - {stock['name']}({stock['code']}) "
                f"涨幅:{stock['pct_chg']:.2f}% "
                f"成交额:{stock['amount']:.0f} "
                f"换手率:{stock['turnover']:.2f}%"
            )

    return lines


def format_report_text(report: List[Dict]) -> str:
    """
    输出为邮件/日志可直接使用的文本
    """
    industry_boards = [x for x in report if x.get("board_type") == "industry"]
    concept_boards = [x for x in report if x.get("board_type") == "concept"]

    # 各自按涨幅排序
    industry_boards = sorted(industry_boards, key=lambda x: x.get("board_pct_chg", 0), reverse=True)
    concept_boards = sorted(concept_boards, key=lambda x: x.get("board_pct_chg", 0), reverse=True)

    lines = []
    lines.append("# 🔥 A股热点板块追踪")
    lines.append("")
    lines.extend(_format_single_section("行业板块 TOP 10（每板块最多 3 只）", industry_boards[:10]))
    lines.append("")
    lines.extend(_format_single_section("概念板块 TOP 10（每板块最多 3 只）", concept_boards[:10]))

    return "\n".join(lines)


if __name__ == "__main__":
    report = build_all_boards_report(
        stock_top_k=3,
        include_industry=True,
        include_concept=True,
        industry_limit=10,
        concept_limit=10,
    )

    print(format_report_text(report))
