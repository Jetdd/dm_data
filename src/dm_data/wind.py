"""Wind W API wrappers — historical, snapshot, sector constituents, hotconcepts.

The local Wind terminal must be running before any call. `start()` is a no-op
after the first successful call (idempotent).

Quick reference
---------------

>>> from dm_data import wind
>>> wind.start()
>>> df = wind.wsd("8841388.WI", "close,amt,low,high,open", "2026-04-23", "2026-05-22", "unit=1")
>>> df = wind.wss(["000001.SZ", "600000.SH"], "sec_name,hotconcept")
>>> df = wind.wset("sectorconstituent", "date=2026-05-22;sectorid=a001010100000000")
>>> df = wind.tdays("2024-01-01", "2024-12-31")
>>> df = wind.edb("M0000545", "2020-01-01", "2024-12-31")

All wrappers return ``pandas.DataFrame`` by default (``usedf=True`` to the
underlying call). For raw `WindData`, pass ``usedf=False``.

Common code aliases (kept for convenience):

    FULL_A_INDEX = "8841388.WI"   # 万得全A — full A-share aggregate index
"""
from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd


FULL_A_INDEX = "8841388.WI"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

_started = False


def _w():
    """Lazy import of WindPy so module import doesn't require Wind."""
    from WindPy import w as _w_obj

    return _w_obj


def start(timeout: int = 30000, show_welcome: bool = False) -> int:
    """Start the Wind connection. Idempotent.

    Returns the Wind ErrorCode (0 on success).
    """
    global _started
    w = _w()
    if _started and w.isconnected():
        return 0
    r = w.start(waitTime=timeout, showmenu=show_welcome)
    _started = r.ErrorCode == 0
    if not _started:
        raise RuntimeError(f"WindPy start failed: {r.ErrorCode} {r.Data}")
    return r.ErrorCode


def stop() -> None:
    global _started
    _w().stop()
    _started = False


def is_connected() -> bool:
    try:
        return bool(_w().isconnected())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Code/field helpers
# ---------------------------------------------------------------------------

def _fmt_codes(codes: str | Iterable[str]) -> str:
    if isinstance(codes, str):
        return codes
    return ",".join(codes)


def _fmt_fields(fields: str | Iterable[str]) -> str:
    if isinstance(fields, str):
        return fields
    return ",".join(fields)


def _ensure_started() -> None:
    if not _started or not is_connected():
        start()


# ---------------------------------------------------------------------------
# Core wrappers
# ---------------------------------------------------------------------------

def wsd(
    codes: str | Sequence[str],
    fields: str | Sequence[str],
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
    options: str = "",
    *,
    usedf: bool = True,
):
    """Historical daily data (Wind WSD).

    Examples
    --------
    >>> wind.wsd("8841388.WI", "close,amt", "2024-01-01", "2024-12-31", "unit=1")
    >>> wind.wsd(["000001.SZ", "600000.SH"], "close,volume", "2024-01-01", "2024-12-31")
    """
    _ensure_started()
    r = _w().wsd(_fmt_codes(codes), _fmt_fields(fields), str(start_date), str(end_date), options, usedf=usedf)
    if usedf:
        err, df = r
        if err != 0:
            raise RuntimeError(f"wsd error {err}: {getattr(df, 'iloc', df)}")
        return df
    return r


def wss(
    codes: str | Sequence[str],
    fields: str | Sequence[str],
    options: str = "",
    *,
    usedf: bool = True,
):
    """Snapshot / point-in-time data (Wind WSS)."""
    _ensure_started()
    r = _w().wss(_fmt_codes(codes), _fmt_fields(fields), options, usedf=usedf)
    if usedf:
        err, df = r
        if err != 0:
            raise RuntimeError(f"wss error {err}: {getattr(df, 'iloc', df)}")
        return df
    return r


def wset(table: str, options: str = "", *, usedf: bool = True):
    """Dataset query (Wind WSET) — sector constituents, futures contracts, etc.

    Examples
    --------
    >>> wind.wset("sectorconstituent", "date=2026-05-22;sectorid=a001010100000000")
    >>> wind.wset("indexconstituent", "date=2026-05-22;windcode=000300.SH")
    """
    _ensure_started()
    r = _w().wset(table, options, usedf=usedf)
    if usedf:
        err, df = r
        if err != 0:
            raise RuntimeError(f"wset error {err}: {getattr(df, 'iloc', df)}")
        return df
    return r


def tdays(
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
    options: str = "",
    *,
    usedf: bool = True,
):
    """Trading-day calendar."""
    _ensure_started()
    r = _w().tdays(str(start_date), str(end_date), options, usedf=usedf)
    if usedf:
        err, df = r
        if err != 0:
            raise RuntimeError(f"tdays error {err}: {df}")
        return df
    return r


def edb(
    codes: str | Sequence[str],
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
    options: str = "",
    *,
    usedf: bool = True,
):
    """Macro EDB time series."""
    _ensure_started()
    r = _w().edb(_fmt_codes(codes), str(start_date), str(end_date), options, usedf=usedf)
    if usedf:
        err, df = r
        if err != 0:
            raise RuntimeError(f"edb error {err}: {df}")
        return df
    return r


# ---------------------------------------------------------------------------
# Convenience: A-share universe + hotconcepts
# ---------------------------------------------------------------------------

def get_full_a(
    fields: str | Sequence[str] = "close,amt,low,high,open",
    start_date: str | pd.Timestamp = "2020-01-01",
    end_date: str | pd.Timestamp | None = None,
    options: str = "unit=1",
) -> pd.DataFrame:
    """Daily aggregate of 万得全A (8841388.WI)."""
    if end_date is None:
        end_date = pd.Timestamp.today().strftime("%Y-%m-%d")
    return wsd(FULL_A_INDEX, fields, start_date, end_date, options)


def get_all_a_codes(date: str | pd.Timestamp | None = None) -> list[str]:
    """All A-share order_book_ids (wind_code) listed on `date` (default today)."""
    if date is None:
        date = pd.Timestamp.today().strftime("%Y-%m-%d")
    # sectorid=a001010100000000 → 全部 A 股
    df = wset("sectorconstituent", f"date={date};sectorid=a001010100000000")
    if df is None or df.empty:
        return []
    col = "wind_code" if "wind_code" in df.columns else df.columns[0]
    return df[col].astype(str).tolist()


def get_hot_concepts(
    codes: Sequence[str] | None = None,
    *,
    trade_date: str | pd.Timestamp | None = None,
    batch_size: int = 100,
    include_name: bool = True,
) -> pd.DataFrame:
    """Pull hotconcept for `codes` (default: all A-share on `trade_date`).

    Returns a long-form DataFrame with columns:
        trade_date, wind_code, stock_name, concept, raw_value

    Combine multiple snapshots over time with
    :func:`dm_data.concepts.save_stock_hotconcept`.
    """
    from .concepts import normalize_hotconcept_frame

    if trade_date is None:
        trade_date = pd.Timestamp.today().strftime("%Y-%m-%d")
    date_str = pd.to_datetime(trade_date).strftime("%Y-%m-%d")

    if codes is None:
        codes = get_all_a_codes(date_str)
    codes = list(codes)
    if not codes:
        return pd.DataFrame(columns=["trade_date", "wind_code", "stock_name", "concept", "raw_value"])

    frames: list[pd.DataFrame] = []
    name_map: pd.DataFrame | None = None
    for i in range(0, len(codes), batch_size):
        batch = codes[i : i + batch_size]
        raw = wss(batch, ("sec_name,hotconcept" if include_name else "hotconcept"),
                  f"tradeDate={date_str.replace('-', '')}")
        if raw is None or raw.empty:
            continue
        if include_name and "SEC_NAME" in raw.columns:
            name_map = raw[["SEC_NAME"]] if name_map is None else pd.concat(
                [name_map, raw[["SEC_NAME"]]]
            )
        frames.append(raw)

    if not frames:
        return pd.DataFrame(columns=["trade_date", "wind_code", "stock_name", "concept", "raw_value"])

    raw_all = pd.concat(frames)
    return normalize_hotconcept_frame(raw_all, date_str, names=name_map)
