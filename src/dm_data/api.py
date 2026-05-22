from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Literal, Sequence

import pandas as pd


Asset = Literal["bond", "stock"]
FrameType = Literal["pandas", "polars", "path"]

DEFAULT_ROOT = Path(r"E:\dm_intraday")
VALID_ASSETS = {"bond", "stock"}
VALID_FREQUENCIES = {"1m", "5m", "15m", "30m", "60m"}
KLINE_TYPES = {"1m": 1, "5m": 2, "15m": 3, "30m": 4, "60m": 5}
_ROOT = Path(os.getenv("DM_INTRADAY_ROOT", str(DEFAULT_ROOT)))


class DataNotFoundError(FileNotFoundError):
    """Raised when a requested symbol/frequency file does not exist."""


class FrequencyError(ValueError):
    """Raised when frequency is not one of the supported DM intraday frequencies."""


class RemoteFetchError(RuntimeError):
    """Raised when local data is missing and DM remote fetch cannot be completed."""


def get_root() -> Path:
    return _ROOT


def set_root(root: str | os.PathLike[str]) -> Path:
    """Set the process-local data root and return it."""
    global _ROOT
    _ROOT = Path(root)
    return _ROOT


def _normalize_asset(asset: str) -> str:
    asset = asset.lower()
    if asset not in VALID_ASSETS:
        raise ValueError(f"asset must be one of {sorted(VALID_ASSETS)}, got {asset!r}")
    return asset


def _normalize_frequency(frequency: str) -> str:
    frequency = frequency.lower()
    aliases = {
        "1min": "1m",
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "60min": "60m",
        "1t": "1m",
        "5t": "5m",
        "15t": "15m",
        "30t": "30m",
        "60t": "60m",
    }
    frequency = aliases.get(frequency, frequency)
    if frequency not in VALID_FREQUENCIES:
        raise FrequencyError(f"frequency must be one of {sorted(VALID_FREQUENCIES)}, got {frequency!r}")
    return frequency


def _normalize_code(code: str) -> str:
    return code.strip()


def parquet_path(
    *,
    asset: str,
    code: str,
    frequency: str = "1m",
    root: str | os.PathLike[str] | None = None,
) -> Path:
    """Return the expected per-symbol parquet path."""
    base = Path(root) if root is not None else _ROOT
    asset = _normalize_asset(asset)
    frequency = _normalize_frequency(frequency)
    code = _normalize_code(code)
    return base / asset / frequency / f"{code}.parquet"


def _detect_datetime_column(columns: Sequence[str]) -> str | None:
    preferred = [
        "datetime",
        "date_time",
        "timestamp",
        "time",
        "issue_datetime",
        "issue_time",
        "trade_time",
        "issue_date",
        "date",
        "trade_date",
    ]
    lower_to_original = {c.lower(): c for c in columns}
    for name in preferred:
        if name in lower_to_original:
            return lower_to_original[name]
    return None


def _filter_datetime(
    df: pd.DataFrame,
    *,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
    datetime_col: str | None,
) -> pd.DataFrame:
    if start_date is None and end_date is None:
        return df

    col = datetime_col or _detect_datetime_column(df.columns)
    if col is None:
        raise ValueError("Cannot filter by date because no datetime/date column was found.")

    values = pd.to_datetime(df[col], errors="coerce")
    mask = pd.Series(True, index=df.index)
    if start_date is not None:
        start = pd.to_datetime(start_date)
        mask &= values >= start
    if end_date is not None:
        end = pd.to_datetime(end_date)
        if end.time() == pd.Timestamp(end.date()).time():
            end = end + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
        mask &= values <= end
    return df.loc[mask].copy()


def _format_dm_datetime(value: str | pd.Timestamp) -> str:
    ts = pd.to_datetime(value)
    if ts.time() == pd.Timestamp(ts.date()).time():
        return ts.date().isoformat()
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def _infer_stock_category(code: str) -> str:
    suffix = code.upper().split(".")[-1] if "." in code else ""
    prefix = code.split(".")[0]
    if suffix in {"SH", "SZ"} and (prefix.startswith(("5", "15", "16", "18"))):
        return "2"
    if suffix in {"SH", "SZ"} and (prefix.startswith(("0", "3", "6", "8", "9"))):
        return "1"
    return "1"


def _remote_payload(
    *,
    asset: str,
    code: str,
    frequency: str,
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
    security_category: str | int | None,
    data_source_list: Sequence[int] | None,
) -> tuple[str, dict[str, object]]:
    kline_type = KLINE_TYPES[frequency]
    if asset == "stock":
        return (
            "/dm-quant-func-service/api/v1/equity/market-data/bars",
            {
                "security_id_list": [code],
                "security_category": str(security_category or _infer_stock_category(code)),
                "kline_type": kline_type,
                "start_datetime": _format_dm_datetime(start_date),
                "end_datetime": _format_dm_datetime(end_date),
            },
        )
    if asset == "bond":
        return (
            "/dm-quant-func-service/api/v1/bond/market-data/bars",
            {
                "security_id_list": [code],
                "data_source_list": list(data_source_list or [1]),
                "kline_type": kline_type,
                "start_datetime": _format_dm_datetime(start_date),
                "end_datetime": _format_dm_datetime(end_date),
            },
        )
    raise ValueError(f"Unsupported asset for remote fetch: {asset}")


def _fetch_remote_price(
    *,
    asset: str,
    code: str,
    frequency: str,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
    security_category: str | int | None,
    data_source_list: Sequence[int] | None,
    timeout: int | float,
) -> pd.DataFrame:
    if start_date is None or end_date is None:
        raise RemoteFetchError("start_date and end_date are required when fetching missing data from DM.")

    try:
        from dm_quant_api_client import DMQuantApiClient
    except ImportError as exc:
        raise RemoteFetchError("dm_quant_api_client is required to fetch missing data from DM.") from exc

    api_path, payload = _remote_payload(
        asset=asset,
        code=code,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        security_category=security_category,
        data_source_list=data_source_list,
    )
    client = DMQuantApiClient(pythonic=True, timeout=timeout)
    try:
        df = client.post_data(data=payload, api_path=api_path)
    finally:
        client.close()
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
    return df


def _read_or_fetch(
    *,
    path: Path,
    asset: str,
    code: str,
    frequency: str,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
    saved: bool,
    missing: Literal["raise", "empty", "fetch"],
    security_category: str | int | None,
    data_source_list: Sequence[int] | None,
    timeout: int | float,
) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)

    if missing == "empty":
        return pd.DataFrame()
    if missing not in {"fetch", "raise"}:
        raise ValueError("missing must be 'fetch', 'raise', or 'empty'")
    if missing == "raise":
        raise DataNotFoundError(f"No local data file: {path}")

    df = _fetch_remote_price(
        asset=asset,
        code=code,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        security_category=security_category,
        data_source_list=data_source_list,
        timeout=timeout,
    )
    if saved:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
    return df


def get_price(
    *,
    asset: str,
    code: str,
    frequency: str = "1m",
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
    fields: Iterable[str] | None = None,
    root: str | os.PathLike[str] | None = None,
    frame_type: FrameType = "pandas",
    datetime_col: str | None = None,
    missing: Literal["fetch", "raise", "empty"] = "fetch",
    saved: bool = True,
    security_category: str | int | None = None,
    data_source_list: Sequence[int] | None = None,
    timeout: int | float = 30,
) -> pd.DataFrame | object | Path:
    """Read one symbol's local intraday bars, fetching from DM if missing.

    Parameters mirror a compact RiceQuant-style call:
    `asset`, `code`, `frequency`, `start_date`, `end_date`.
    """
    asset = _normalize_asset(asset)
    frequency = _normalize_frequency(frequency)
    code = _normalize_code(code)
    path = parquet_path(asset=asset, code=code, frequency=frequency, root=root)
    if frame_type == "path":
        return path

    df = _read_or_fetch(
        path=path,
        asset=asset,
        code=code,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        saved=saved,
        missing=missing,
        security_category=security_category,
        data_source_list=data_source_list,
        timeout=timeout,
    )
    df = _filter_datetime(df, start_date=start_date, end_date=end_date, datetime_col=datetime_col)

    if fields is not None:
        selected = list(fields)
        missing_fields = [field for field in selected if field not in df.columns]
        if missing_fields:
            raise KeyError(f"Fields not found in {path.name}: {missing_fields}")
        df = df[selected]

    if frame_type == "pandas":
        return df
    if frame_type == "polars":
        import polars as pl

        return pl.from_pandas(df)
    raise ValueError("frame_type must be 'pandas', 'polars', or 'path'")


def list_symbols(
    *,
    asset: str,
    frequency: str = "1m",
    root: str | os.PathLike[str] | None = None,
) -> list[str]:
    base = Path(root) if root is not None else _ROOT
    asset = _normalize_asset(asset)
    frequency = _normalize_frequency(frequency)
    folder = base / asset / frequency
    if not folder.exists():
        return []
    return sorted(path.stem for path in folder.glob("*.parquet"))
