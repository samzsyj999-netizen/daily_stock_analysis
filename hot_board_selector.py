from typing import List, Dict


def get_hot_boards() -> List[Dict]:
    """
    这里将来要替换成项目现有的板块榜数据接口。
    先用示例结构表示：
    [
        {"name": "机器人", "pct_chg": 4.8, "amount_rank": 1},
        {"name": "算力", "pct_chg": 3.9, "amount_rank": 2},
    ]
    """
    # TODO: 接入项目现有的板块涨跌榜数据
    return []


def get_board_stocks(board_name: str) -> List[Dict]:
    """
    这里将来要替换成“获取某个板块成分股”的真实接口。
    返回结构示例：
    [
        {"code": "300024", "name": "机器人", "pct_chg": 8.5, "amount": 1200000000, "turnover": 12.4},
        {"code": "002747", "name": "埃斯顿", "pct_chg": 5.2, "amount": 900000000, "turnover": 8.7},
    ]
    """
    # TODO: 接入项目现有的数据源
    return []


def pick_top_stocks(board_stocks: List[Dict], top_k: int = 3) -> List[Dict]:
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


def build_hot_stock_pool(board_top_n: int = 3, stock_top_k: int = 3) -> List[Dict]:
    hot_boards = get_hot_boards()
    hot_boards = sorted(hot_boards, key=lambda b: b.get("pct_chg", 0), reverse=True)[:board_top_n]

    final_stocks = []
    for board in hot_boards:
        board_name = board["name"]
        stocks = get_board_stocks(board_name)
        top_stocks = pick_top_stocks(stocks, top_k=stock_top_k)

        for s in top_stocks:
            s["board_name"] = board_name
            final_stocks.append(s)

    return final_stocks
