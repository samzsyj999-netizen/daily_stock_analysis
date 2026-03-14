from typing import List, Dict


def get_hot_boards() -> List[Dict]:
    """
    这里以后要接你项目里真实的板块数据。
    先保留这个函数名，后面替换内部实现。
    返回格式示例：
    [
        {"name": "机器人", "pct_chg": 4.8},
        {"name": "算力", "pct_chg": 3.6},
    ]
    """
    return []


def get_board_stocks(board_name: str) -> List[Dict]:
    """
    这里以后要接你项目里真实的‘板块成分股’数据。
    返回格式示例：
    [
        {"code": "300024", "name": "机器人", "pct_chg": 8.5, "amount": 1200000000, "turnover": 12.4},
        {"code": "002747", "name": "埃斯顿", "pct_chg": 5.2, "amount": 900000000, "turnover": 8.7},
    ]
    """
    return []


def pick_top_stocks(board_stocks: List[Dict], top_k: int = 3) -> List[Dict]:
    """
    每个板块只挑 3 只代表股。
    筛选逻辑：
    1. 去掉 ST
    2. 去掉停牌
    3. 按涨幅、成交额、换手率排序
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


def build_hot_stock_pool(stock_top_k: int = 3) -> List[Dict]:
    """
    核心函数：
    1. 取所有热门板块
    2. 不限制板块数量
    3. 每个板块取 top_k 只代表股
    """
    hot_boards = get_hot_boards()
    hot_boards = sorted(hot_boards, key=lambda b: b.get("pct_chg", 0), reverse=True)

    final_stocks = []
    for board in hot_boards:
        board_name = board["name"]
        board_stocks = get_board_stocks(board_name)
        top_stocks = pick_top_stocks(board_stocks, top_k=stock_top_k)

        for s in top_stocks:
            s["board_name"] = board_name
            final_stocks.append(s)

    return final_stocks
