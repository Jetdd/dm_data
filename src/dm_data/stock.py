from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .api import get_price as _get_price
from .api import _dedupe_sort
from .api import _detect_datetime_column
from .api import _fetch_remote_price
from .api import _filter_datetime
from .api import _normalize_frequency
from .api import list_symbols as _list_symbols
from .api import parquet_path as _parquet_path


def get_price(code: str, frequency: str = "1m", start_date=None, end_date=None, **kwargs):
    return _get_price(
        asset="stock",
        code=code,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        **kwargs,
    )


def list_symbols(frequency: str = "1m", **kwargs) -> list[str]:
    return _list_symbols(asset="stock", frequency=frequency, **kwargs)


def parquet_path(code: str, frequency: str = "1m", **kwargs):
    return _parquet_path(asset="stock", code=code, frequency=frequency, **kwargs)


def _path_for(code: str, frequency: str, root=None) -> Path:
    return _parquet_path(asset="stock", code=code, frequency=frequency, root=root)


def _last_timestamp(df: pd.DataFrame, datetime_col: str | None = None) -> pd.Timestamp | None:
    if df.empty:
        return None
    col = datetime_col or _detect_datetime_column(df.columns)
    if col is None:
        return None
    values = pd.to_datetime(df[col], errors="coerce").dropna()
    if values.empty:
        return None
    return pd.Timestamp(values.max())


def _default_update_start(last_ts: pd.Timestamp | None, overlap_days: int) -> pd.Timestamp | None:
    if last_ts is None:
        return None
    if overlap_days > 0:
        return last_ts.normalize() - pd.Timedelta(days=overlap_days - 1)
    return last_ts.normalize() + pd.Timedelta(days=1)


def update_price(
    code: str,
    frequency: str = "1d",
    *,
    start_date=None,
    end_date=None,
    root=None,
    overlap_days: int = 5,
    saved: bool = True,
    security_category=None,
    timeout: int | float = 30,
    datetime_col: str | None = None,
) -> dict:
    """Update one existing local stock parquet file from DM.

    By default the function refreshes the last 5 calendar days in the local
    file and appends any newer remote bars. This handles both new bars and
    vendor corrections to the most recent rows.
    """
    frequency = _normalize_frequency(frequency)
    path = _path_for(code, frequency, root=root)
    if not path.exists():
        raise FileNotFoundError(f"No existing local stock file: {path}")
    if overlap_days < 0:
        raise ValueError("overlap_days must be >= 0")

    local = pd.read_parquet(path)
    before_rows = len(local)
    last_before = _last_timestamp(local, datetime_col=datetime_col)

    fetch_start = pd.to_datetime(start_date) if start_date is not None else _default_update_start(last_before, overlap_days)
    fetch_end = pd.to_datetime(end_date) if end_date is not None else pd.Timestamp.today().normalize()
    if fetch_start is None:
        raise ValueError(f"Cannot detect last timestamp in {path}")

    if fetch_start > fetch_end:
        return {
            "code": code,
            "frequency": frequency,
            "path": str(path),
            "status": "skipped",
            "reason": "already current for requested end_date",
            "rows_before": before_rows,
            "rows_after": before_rows,
            "rows_fetched": 0,
            "last_before": last_before,
            "last_after": last_before,
            "fetch_start": fetch_start,
            "fetch_end": fetch_end,
        }

    fetched = _fetch_remote_price(
        asset="stock",
        code=code,
        frequency=frequency,
        start_date=fetch_start,
        end_date=fetch_end,
        security_category=security_category,
        data_source_list=None,
        timeout=timeout,
    )
    if fetched is None:
        fetched = pd.DataFrame()
    if not isinstance(fetched, pd.DataFrame):
        fetched = pd.DataFrame(fetched)

    if fetched.empty:
        merged = local
    else:
        merged = _dedupe_sort(pd.concat([local, fetched], ignore_index=True), datetime_col=datetime_col)

    if saved and not fetched.empty:
        path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(path, index=False)

    last_after = _last_timestamp(merged, datetime_col=datetime_col)
    return {
        "code": code,
        "frequency": frequency,
        "path": str(path),
        "status": "updated" if not fetched.empty else "empty",
        "reason": "",
        "rows_before": before_rows,
        "rows_after": len(merged),
        "rows_fetched": len(fetched),
        "last_before": last_before,
        "last_after": last_after,
        "fetch_start": fetch_start,
        "fetch_end": fetch_end,
    }


def update_existing(
    codes: Iterable[str] | None = None,
    frequency: str = "1d",
    *,
    start_date=None,
    end_date=None,
    root=None,
    overlap_days: int = 5,
    continue_on_error: bool = True,
    timeout: int | float = 30,
    security_category=None,
) -> pd.DataFrame:
    """Update all existing local stock files for a frequency.

    Parameters
    ----------
    codes:
        Optional stock code list. When omitted, all existing parquet files under
        ``{root}/stock/{frequency}`` are updated.
    frequency:
        DM frequency, e.g. ``1d`` / ``1m``.
    overlap_days:
        Number of trailing calendar days to refetch for each symbol. Use 0 to
        fetch only strictly newer dates.
    continue_on_error:
        If True, errors are recorded in the returned summary DataFrame.
    """
    frequency = _normalize_frequency(frequency)
    selected = list(codes) if codes is not None else _list_symbols(asset="stock", frequency=frequency, root=root)
    rows: list[dict] = []
    for code in selected:
        try:
            rows.append(
                update_price(
                    code,
                    frequency=frequency,
                    start_date=start_date,
                    end_date=end_date,
                    root=root,
                    overlap_days=overlap_days,
                    saved=True,
                    security_category=security_category,
                    timeout=timeout,
                )
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            path = _path_for(code, frequency, root=root)
            rows.append({
                "code": code,
                "frequency": frequency,
                "path": str(path),
                "status": "error",
                "reason": f"{type(exc).__name__}: {exc}",
                "rows_before": None,
                "rows_after": None,
                "rows_fetched": 0,
                "last_before": None,
                "last_after": None,
                "fetch_start": pd.to_datetime(start_date) if start_date is not None else None,
                "fetch_end": pd.to_datetime(end_date) if end_date is not None else None,
            })
    return pd.DataFrame(rows)


def update_and_load(
    code: str,
    frequency: str = "1d",
    *,
    start_date=None,
    end_date=None,
    root=None,
    overlap_days: int = 5,
    fields: Iterable[str] | None = None,
    **kwargs,
) -> pd.DataFrame:
    """Update one existing stock file, then return the requested local slice."""
    update_price(
        code,
        frequency=frequency,
        start_date=None,
        end_date=end_date,
        root=root,
        overlap_days=overlap_days,
        **kwargs,
    )
    df = pd.read_parquet(_path_for(code, _normalize_frequency(frequency), root=root))
    df = _filter_datetime(df, start_date=start_date, end_date=end_date, datetime_col=None)
    if fields is not None:
        df = df[list(fields)]
    return df
