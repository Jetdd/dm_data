from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from dm_data.concepts import normalize_hotconcept_frame, save_stock_hotconcept


DEFAULT_SECTOR_ID = "a001010100000000"
NAME_COLUMNS = {"sec_name", "SEC_NAME", "name", "S_INFO_NAME", "证券简称"}


def _yyyymmdd(value: str) -> str:
    return pd.to_datetime(value).strftime("%Y%m%d")


def _has_name_column(df: pd.DataFrame) -> bool:
    return any(col in NAME_COLUMNS for col in df.columns)


def _fetch_names(w, codes: list[str], batch_size: int) -> pd.DataFrame:
    frames = []
    for i in range(0, len(codes), batch_size):
        batch = codes[i : i + batch_size]
        err, df = w.wss(",".join(batch), "sec_name", usedf=True)
        if err != 0:
            raise SystemExit(f"Wind wss sec_name failed at batch {i // batch_size + 1}, error={err}")
        frames.append(df)
    out = pd.concat(frames, axis=0) if frames else pd.DataFrame()
    out = out.reset_index().rename(columns={"index": "wind_code"})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Wind A-share hot concepts into dm_intraday mapping parquet.")
    parser.add_argument("--date", default=pd.Timestamp.today().date().isoformat(), help="Sector constituent date, e.g. 2026-05-22")
    parser.add_argument("--trade-date", help="Wind wss hotconcept tradeDate. Defaults to --date.")
    parser.add_argument("--sector-id", default=DEFAULT_SECTOR_ID, help="Wind sector id for all A shares.")
    parser.add_argument("--root", default=None, help="dm_intraday root, default uses E:\\dm_intraday or DM_INTRADAY_ROOT")
    parser.add_argument("--batch-size", type=int, default=3500, help="WSS code batch size.")
    args = parser.parse_args()

    try:
        from WindPy import w
    except ImportError as exc:
        raise SystemExit("WindPy is not importable in this Python environment.") from exc

    date = pd.to_datetime(args.date).date().isoformat()
    trade_date = pd.to_datetime(args.trade_date or args.date).date().isoformat()
    date_param = _yyyymmdd(date)
    trade_date_param = _yyyymmdd(trade_date)

    w.start()

    err, codes = w.wset(
        "sectorconstituent",
        f"date={date};sectorid={args.sector_id}",
        usedf=True,
    )
    if err != 0:
        raise SystemExit(f"Wind wset sectorconstituent failed, error={err}")
    if "wind_code" not in codes.columns:
        raise SystemExit(f"Wind sectorconstituent result has no wind_code column: {list(codes.columns)}")

    all_codes = codes["wind_code"].dropna().astype(str).unique().tolist()
    names = codes if _has_name_column(codes) else _fetch_names(w, all_codes, args.batch_size)
    frames = []
    for i in range(0, len(all_codes), args.batch_size):
        batch = all_codes[i : i + args.batch_size]
        c_str = ",".join(batch)
        err, df = w.wss(c_str, "hotconcept", f"tradeDate={trade_date_param}", usedf=True)
        if err != 0:
            raise SystemExit(f"Wind wss hotconcept failed at batch {i // args.batch_size + 1}, error={err}")
        frames.append(df)

    raw = pd.concat(frames, axis=0) if frames else pd.DataFrame()
    mapping = normalize_hotconcept_frame(raw, trade_date=trade_date, names=names)
    path = save_stock_hotconcept(mapping, raw=raw, root=args.root, replace_date=True)

    print(f"codes={len(all_codes)}")
    print(f"mapping_rows={len(mapping)}")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
