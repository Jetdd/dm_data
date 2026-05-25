"""Batch update existing rqdatac-format stock daily parquet files.

This script is intentionally focused on the existing local layout:
    {root}/stock/1d/{order_book_id}.parquet
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd
import rqdatac as rq


DEFAULT_ROOT = Path(r"C:\projects\data_new")


def _merge_one(path: Path, incoming: pd.DataFrame) -> dict:
    old = pd.read_parquet(path)
    before_rows = len(old)
    old["date"] = pd.to_datetime(old["date"])
    incoming = incoming.copy()
    incoming["date"] = pd.to_datetime(incoming["date"])

    merged = pd.concat([old, incoming], ignore_index=True)
    keys = [c for c in ["order_book_id", "date"] if c in merged.columns]
    if not keys:
        keys = ["date"]
    merged = merged.drop_duplicates(keys, keep="last").sort_values("date").reset_index(drop=True)
    merged.to_parquet(path, index=False)
    return {
        "code": path.stem,
        "status": "updated",
        "rows_before": before_rows,
        "rows_after": len(merged),
        "rows_added": len(merged) - before_rows,
        "last_after": merged["date"].max(),
    }


def update_existing_stock_1d(
    *,
    root: Path,
    start_date: str,
    end_date: str,
    batch_size: int,
    user: str,
    password: str,
) -> pd.DataFrame:
    stock_dir = root / "stock" / "1d"
    codes = sorted(p.stem for p in stock_dir.glob("*.parquet"))
    if not codes:
        raise RuntimeError(f"No parquet files found under {stock_dir}")

    rq.init(user, password)
    rows: list[dict] = []
    for i in range(0, len(codes), batch_size):
        batch = codes[i: i + batch_size]
        t0 = time.time()
        try:
            df = rq.get_price(
                batch,
                start_date=start_date,
                end_date=end_date,
                frequency="1d",
                fields=None,
                adjust_type="pre",
            )
            if df is None or len(df) == 0:
                for code in batch:
                    rows.append({"code": code, "status": "empty", "rows_added": 0})
            elif isinstance(df.index, pd.MultiIndex):
                for code, sub in df.groupby(level=0):
                    sub = sub.reset_index()
                    rows.append(_merge_one(stock_dir / f"{code}.parquet", sub))
            else:
                sub = df.reset_index()
                rows.append(_merge_one(stock_dir / f"{batch[0]}.parquet", sub))
            print(f"[batch] {i + len(batch):>5}/{len(codes)} done in {time.time() - t0:.1f}s", flush=True)
        except Exception as exc:
            for code in batch:
                rows.append({"code": code, "status": "error", "reason": f"{type(exc).__name__}: {exc}", "rows_added": 0})
            print(f"[batch] {i + len(batch):>5}/{len(codes)} error: {exc}", flush=True)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--start", default=pd.Timestamp.today().strftime("%Y%m%d"))
    parser.add_argument("--end", default=pd.Timestamp.today().strftime("%Y%m%d"))
    parser.add_argument("--batch-size", type=int, default=300)
    parser.add_argument("--user", default=os.getenv("RQDATAC_USER") or os.getenv("RQDATAC_USERNAME"))
    parser.add_argument("--password", default=os.getenv("RQDATAC_PASSWORD"))
    parser.add_argument("--summary", default=None)
    args = parser.parse_args()

    if not args.user or not args.password:
        raise SystemExit("rqdatac credentials required: pass --user/--password or set RQDATAC_USER/RQDATAC_PASSWORD")

    root = Path(args.root)
    summary = update_existing_stock_1d(
        root=root,
        start_date=args.start,
        end_date=args.end,
        batch_size=args.batch_size,
        user=args.user,
        password=args.password,
    )
    out = Path(args.summary) if args.summary else root / "stock" / f"update_stock_1d_rqdatac_{args.end}.csv"
    summary.to_csv(out, index=False, encoding="utf-8-sig")
    print(summary["status"].value_counts(dropna=False).to_string())
    print(f"rows={len(summary)}")
    print(f"summary={out}")


if __name__ == "__main__":
    main()
