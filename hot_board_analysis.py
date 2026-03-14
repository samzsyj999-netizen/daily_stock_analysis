from typing import List, Dict, Literal, Callable
import time
import logging
import akshare as ak


logger = logging.getLogger(__name__)

BoardType = Literal["industry", "concept"]

DEFAULT_INDUSTRY_LIMIT = 3
DEFAULT_CONCEPT_LIMIT = 3


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
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            logger.warning(f"[热点板块] 第 {attempt}/{retries} 次请求失败: {e}")
            if attempt < retries:
                time.sleep(sleep_seconds)
    raise last_error


def get_hot_boards(board_type: BoardType = "industry") -> List[Dict]:
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
            "board_name": board_name,
            "board_type": board_type,
            "board_pct_chg": safe_float(row.get("涨跌幅", 0)),
        })

    results.sort(key=lambda x: x["board_pct_chg"], reverse=True)
    return results


def build_hot_board_report(
    board_type: BoardType = "industry",
    board_limit: int | None = None,
) -> List[Dict]:
    hot_boards = get_hot_boards(board_type=board_type)

    if board_limit is not None:
        hot_boards = hot_boards[:board_limit]

    report = []
    for board in hot_boards:
        report.append({
            "board_name": board["board_name"],
            "board_type": board["board_type"],
            "board_pct_chg": board["board_pct_chg"],
        })

    return report


def build_all_boards_report(
    include_industry: bool = True,
    include_concept: bool = True,
    industry_limit: int | None = DEFAULT_INDUSTRY_LIMIT,
    concept_limit: int | None = DEFAULT_CONCEPT_LIMIT,
) -> List[Dict]:
    final_report = []

    if include_industry:
        try:
            final_report.extend(
                build_hot_board_report(
                    board_type="industry",
                    board_limit=industry_limit,
                )
            )
        except Exception as e:
            logger.warning(f"[热点板块] 获取行业板块失败: {e}")
            final_report.append({
                "board_name": f"行业板块获取失败: {e}",
                "board_type": "industry",
                "board_pct_chg": 0.0,
            })

    if include_concept:
        try:
            final_report.extend(
                build_hot_board_report(
                    board_type="concept",
                    board_limit=concept_limit,
                )
            )
        except Exception as e:
            logger.warning(f"[热点板块] 获取概念板块失败: {e}")
            final_report.append({
                "board_name": f"概念板块获取失败: {e}",
                "board_type": "concept",
                "board_pct_chg": 0.0,
            })

    return final_report


def format_report_text(report: List[Dict]) -> str:
    lines = []
    lines.append("# 🔥 A股热点板块追踪")
    lines.append("")

    industry_boards = [x for x in report if x.get("board_type") == "industry"]
    concept_boards = [x for x in report if x.get("board_type") == "concept"]

    lines.append("## 行业板块 TOP 3")
    if not industry_boards:
        lines.append("- 暂无数据")
    else:
        for idx, board in enumerate(industry_boards[:3], start=1):
            lines.append(
                f"{idx}. {board['board_name']} | 涨幅: {board['board_pct_chg']:.2f}%"
            )

    lines.append("")
    lines.append("## 概念板块 TOP 3")
    if not concept_boards:
        lines.append("- 暂无数据")
    else:
        for idx, board in enumerate(concept_boards[:3], start=1):
            lines.append(
                f"{idx}. {board['board_name']} | 涨幅: {board['board_pct_chg']:.2f}%"
            )

    return "\n".join(lines)


if __name__ == "__main__":
    report = build_all_boards_report(
        include_industry=True,
        include_concept=True,
        industry_limit=3,
        concept_limit=3,
    )
    print(format_report_text(report))
