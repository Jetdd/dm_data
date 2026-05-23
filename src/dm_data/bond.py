from __future__ import annotations

from .api import get_price as _get_price
from .api import list_symbols as _list_symbols
from .api import parquet_path as _parquet_path


def get_price(code: str, frequency: str = "1m", start_date=None, end_date=None, **kwargs):
    return _get_price(
        asset="bond",
        code=code,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        **kwargs,
    )


def list_symbols(frequency: str = "1m", **kwargs) -> list[str]:
    return _list_symbols(asset="bond", frequency=frequency, **kwargs)


def parquet_path(code: str, frequency: str = "1m", **kwargs):
    return _parquet_path(asset="bond", code=code, frequency=frequency, **kwargs)
