from __future__ import annotations

from typing import Literal, Sequence

import pandas as pd

from .config import get_config


def _ensure_rqdatac() -> None:
    get_config().init_rqdatac()


# ---------------------------------------------------------------------------
# 主力合约与连续行情（含复权）
# ---------------------------------------------------------------------------

def get_dominant(
    underlying_symbol: str | Sequence[str],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    rule: Literal[0, 1, 2] = 0,
    rank: Literal[1, 2, 3] = 1,
    market: str = "cn",
) -> pd.Series | pd.DataFrame | None:
    """获取指定期货品种对应的主力合约。

    :param underlying_symbol: 品种代码，如 'IM' 'IF' 'IC'
    :param start_date: 开始日期，如 '2024-01-01'
    :param end_date: 结束日期，如 '2024-12-31'
    :param rule: 主力合约规则
        0 – 曾做过主力的合约被换下后不会再被选上（默认）
        1 – 持仓量最大，超过当前主力1.1倍时次日切换
        2 – 前一交易日持仓量与成交量均为最大
    :param rank: 1=主力, 2=次主力, 3=次次主力
    :param market: 默认 'cn'
    :returns: pandas.Series（index=date, value=dominant_contract）
    """
    _ensure_rqdatac()
    import rqdatac

    return rqdatac.futures.get_dominant(
        underlying_symbol, start_date, end_date, rule=rule, rank=rank, market=market
    )


def get_dominant_price(
    underlying_symbols: str | Sequence[str],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    frequency: str = "1d",
    fields: Sequence[str] | None = None,
    adjust_type: Literal["none", "pre", "post"] = "pre",
    adjust_method: Literal[
        "prev_close_spread", "open_spread", "prev_close_ratio", "open_ratio"
    ] = "prev_close_spread",
    rule: Literal[0, 1, 2] = 0,
) -> pd.DataFrame | None:
    """获取期货主力合约行情数据，支持复权。

    :param underlying_symbols: 品种代码，如 'IM' / ['IM', 'IF']
    :param start_date: 最小支持 2010-01-04
    :param end_date:
    :param frequency: '1d' / '1m' / '5m' / ... / 'tick'
    :param fields: 指定字段列表，None 返回全部
    :param adjust_type: 'none' 不复权, 'pre' 前复权（默认）, 'post' 后复权
    :param adjust_method:
        'prev_close_spread' – 基于昨收价差复权（默认）
        'open_spread'       – 基于开盘价差复权
        'prev_close_ratio'  – 基于昨收比例复权
        'open_ratio'        – 基于开盘比例复权
    :param rule: 主力合约规则，同 get_dominant
    :returns: MultiIndex DataFrame (underlying_symbol, date/datetime)
    """
    _ensure_rqdatac()
    import rqdatac

    return rqdatac.futures.get_dominant_price(
        underlying_symbols,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        fields=list(fields) if fields is not None else None,
        adjust_type=adjust_type,
        adjust_method=adjust_method,
        rule=rule,
    )


# ---------------------------------------------------------------------------
# 通用行情
# ---------------------------------------------------------------------------

def get_price(
    order_book_ids: str | Sequence[str],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    frequency: str = "1d",
    fields: Sequence[str] | None = None,
    adjust_type: Literal["none", "pre", "post", "pre_volume", "post_volume", "internal"] = "pre",
    market: str = "cn",
) -> pd.DataFrame | None:
    """获取期货（或股票）历史行情。

    :param order_book_ids: 合约代码，如 'IM2506.CCFX' 或 'IM8888.CCFX'（连续合约）
    :param adjust_type: 'pre' 前复权, 'post' 后复权, 'none' 不复权
    """
    _ensure_rqdatac()
    import rqdatac

    return rqdatac.get_price(
        order_book_ids,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        fields=list(fields) if fields is not None else None,
        adjust_type=adjust_type,
        market=market,
    )


def get_contracts(
    underlying_symbol: str,
    *,
    date: str | None = None,
    market: str = "cn",
) -> pd.DataFrame | None:
    """获取某品种在指定日期的全部可交易合约列表。"""
    _ensure_rqdatac()
    import rqdatac

    return rqdatac.get_future_contracts(underlying_symbol, date=date, market=market)


# ---------------------------------------------------------------------------
# 交易参数与成本
# ---------------------------------------------------------------------------

def get_commission_margin(
    order_book_ids: str | Sequence[str] | None = None,
    *,
    fields: Sequence[str] | None = None,
    hedge_flag: Literal["speculation", "hedge", "arbitrage"] = "speculation",
) -> pd.DataFrame | None:
    """获取期货保证金和手续费数据。

    :param order_book_ids: 合约代码或列表，None 表示全部合约
    :param fields: 可选 'margin_type', 'long_margin_ratio', 'short_margin_ratio',
        'commission_type', 'open_commission_ratio', 'close_commission_ratio',
        'close_commission_today_ratio'
    :param hedge_flag: 'speculation'（默认）/ 'hedge' / 'arbitrage'
    """
    _ensure_rqdatac()
    import rqdatac

    return rqdatac.futures.get_commission_margin(
        order_book_ids, fields=list(fields) if fields is not None else None, hedge_flag=hedge_flag
    )


def get_trading_parameters(
    order_book_ids: str | Sequence[str],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    fields: Sequence[str] | None = None,
    market: str = "cn",
) -> pd.DataFrame | None:
    """获取期货交易参数（保证金率、手续费、限仓等）。"""
    _ensure_rqdatac()
    import rqdatac

    return rqdatac.futures.get_trading_parameters(
        order_book_ids,
        start_date=start_date,
        end_date=end_date,
        fields=list(fields) if fields is not None else None,
        market=market,
    )


# ---------------------------------------------------------------------------
# 持仓排名与仓单
# ---------------------------------------------------------------------------

def get_member_rank(
    obj: str,
    *,
    trading_date: str | None = None,
    rank_by: Literal["volume", "long", "short"] = "volume",
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame | None:
    """获取期货会员排名数据。

    :param obj: 合约代码或品种代码
    :param trading_date: 查询日期（与 start_date/end_date 二选一）
    :param rank_by: 'volume' / 'long' / 'short'
    :param start_date: 区间查询开始日期
    :param end_date: 区间查询结束日期
    """
    _ensure_rqdatac()
    import rqdatac

    if start_date and end_date:
        return rqdatac.futures.get_member_rank(
            obj, start_date=start_date, end_date=end_date, rank_by=rank_by
        )
    return rqdatac.futures.get_member_rank(obj, trading_date=trading_date, rank_by=rank_by)


def get_warehouse_stocks(
    underlying_symbols: str | Sequence[str],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    market: str = "cn",
) -> pd.DataFrame | None:
    """获取期货注册仓单数据。"""
    _ensure_rqdatac()
    import rqdatac

    return rqdatac.futures.get_warehouse_stocks(
        underlying_symbols, start_date=start_date, end_date=end_date, market=market
    )


# ---------------------------------------------------------------------------
# 股指期货基差
# ---------------------------------------------------------------------------

def get_basis(
    order_book_ids: str | Sequence[str],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    fields: Sequence[str] | None = None,
    frequency: Literal["1d", "1m", "tick"] = "1d",
    market: str = "cn",
) -> pd.DataFrame | None:
    """获取股指期货升贴水（基差）数据。

    :param order_book_ids: 股指期货合约，如 'IF2506.CCFX'
    :param frequency: '1d' / '1m' / 'tick'
    """
    _ensure_rqdatac()
    import rqdatac

    return rqdatac.futures.get_basis(
        order_book_ids,
        start_date=start_date,
        end_date=end_date,
        fields=list(fields) if fields is not None else None,
        frequency=frequency,
        market=market,
    )


def get_current_basis(
    order_book_ids: str | Sequence[str],
    *,
    market: str = "cn",
) -> pd.DataFrame | None:
    """获取股指期货实时基差指标。"""
    _ensure_rqdatac()
    import rqdatac

    return rqdatac.futures.get_current_basis(order_book_ids, market=market)


# ---------------------------------------------------------------------------
# 复权因子
# ---------------------------------------------------------------------------

def get_ex_factor(
    underlying_symbols: str | Sequence[str],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    adjust_method: Literal[
        "prev_close_spread", "open_spread", "prev_close_ratio", "open_ratio"
    ] = "prev_close_spread",
    rule: Literal[0, 1, 2] = 0,
    market: str = "cn",
) -> pd.DataFrame | None:
    """获取期货复权因子。"""
    _ensure_rqdatac()
    import rqdatac

    return rqdatac.futures.get_ex_factor(
        underlying_symbols,
        start_date=start_date,
        end_date=end_date,
        adjust_method=adjust_method,
        rule=rule,
        market=market,
    )
