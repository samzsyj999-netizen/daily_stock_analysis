from typing import List, Dict, Literal, Callable
import time
import logging
import akshare as ak
import pandas as pd

# 设置日志
logger = logging.getLogger(__name__)

# 定义板块类型
BoardType = Literal["industry", "concept"]

# 设置默认参数
DEFAULT_TOP_K = 0  # 去掉了固定选 3 个股票的功能
DEFAULT_INDUSTRY_LIMIT = 5  # 行业板块限制为 5
DEFAULT_CONCEPT_LIMIT = 5  # 概念板块限制为 5

# 安全转换为浮动值
def safe_float(value, default=0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip()
        if value in ("", "-", "--", "None", "nan"):
            return default
        return float(value)
    except:
        return default

# 获取热门板块报告
def build_hot_board_report(
        stock_top_k: int = DEFAULT_TOP_K,  # 股票推荐数（去掉3只股票功能）
        include_industry: bool = True,
        include_concept: bool = True,
        industry_limit: int = DEFAULT_INDUSTRY_LIMIT,
        concept_limit: int = DEFAULT_CONCEPT_LIMIT,
) -> Dict:
    """
    获取热门板块数据

    :param stock_top_k: 每个板块推荐的股票数
    :param include_industry: 是否包含行业板块
    :param include_concept: 是否包含概念板块
    :param industry_limit: 行业板块限制数
    :param concept_limit: 概念板块限制数
    :return: 热门板块报告
    """
    board_report = []
    
    # 获取行业板块数据
    if include_industry:
        try:
            industry_data = ak.stock_board_industry_name()
            industry_data = industry_data.head(industry_limit)  # 获取限制数目的行业板块
            for _, row in industry_data.iterrows():
                board_report.append({
                    "name": row['板块名称'],
                    "type": "industry",
                    "pct_chg": row['涨幅'],
                    "error": None
                })
        except Exception as e:
            logger.warning(f"[行业板块] 获取行业板块失败: {e}")

    # 获取概念板块数据
    if include_concept:
        try:
            concept_data = ak.stock_board_concept_name()
            concept_data = concept_data.head(concept_limit)  # 获取限制数目的概念板块
            for _, row in concept_data.iterrows():
                board_report.append({
                    "name": row['板块名称'],
                    "type": "concept",
                    "pct_chg": row['涨幅'],
                    "error": None
                })
        except Exception as e:
            logger.warning(f"[概念板块] 获取概念板块失败: {e}")

    return board_report


# 格式化报告文本
def format_report_text(board_report: List[Dict]) -> str:
    """
    格式化报告文本

    :param board_report: 热门板块报告
    :return: 格式化后的报告文本
    """
    lines = []
    for board in board_report:
        lines.append(f"## {board['name']} ({board['type']})")
        lines.append(f"涨幅: {board['pct_chg']:.2f}%")
        lines.append("")
    return "\n".join(lines)


# 主函数
def main() -> int:
    """
    主入口函数

    Returns:
        退出码（0 表示成功）
    """
    # 定义报告的基本格式
    hot_board_text = ""
    try:
        board_report = build_hot_board_report(
            stock_top_k=0,  # 去掉推荐 3 只股票的功能
            include_industry=True,
            include_concept=True,
            industry_limit=DEFAULT_INDUSTRY_LIMIT,
            concept_limit=DEFAULT_CONCEPT_LIMIT,
        )
        hot_board_text = format_report_text(board_report)
        logger.info("\n" + hot_board_text)
    except Exception as e:
        hot_board_text = f"🔥 热点板块分析失败\n\n错误信息：{e}"
        logger.warning(f"热门板块分析失败，已跳过: {e}")
    
    # 创建快照
    save_context_snapshot = None
    return 0


if __name__ == "__main__":
    main()
