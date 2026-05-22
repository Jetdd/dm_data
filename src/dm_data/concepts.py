from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .api import get_root


CONCEPT_FILE = Path("meta") / "symbols" / "stock_hotconcept.parquet"
RAW_CONCEPT_FILE = Path("meta") / "symbols" / "stock_hotconcept_raw.parquet"
_DELIMITER_RE = re.compile(r"[;,，；|/、]+")


def concept_path(root: str | Path | None = None) -> Path:
    base = Path(root) if root is not None else get_root()
    return base / CONCEPT_FILE


def raw_concept_path(root: str | Path | None = None) -> Path:
    base = Path(root) if root is not None else get_root()
    return base / RAW_CONCEPT_FILE


def split_concepts(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = [part.strip() for part in _DELIMITER_RE.split(text)]
    return [part for part in parts if part and part.lower() not in {"nan", "none"}]


def _parse_trade_date(value: str | pd.Timestamp) -> str:
    text = str(value)
    if re.fullmatch(r"\d{8}", text):
        return pd.to_datetime(text, format="%Y%m%d").date().isoformat()
    return pd.to_datetime(value).date().isoformat()


def normalize_hotconcept_frame(
    raw: pd.DataFrame,
    trade_date: str | pd.Timestamp,
    names: pd.DataFrame | dict[str, str] | None = None,
) -> pd.DataFrame:
    """Convert Wind wss hotconcept output to long concept membership rows."""
    if raw.empty:
        return pd.DataFrame(columns=["trade_date", "wind_code", "stock_name", "concept", "raw_value"])

    df = raw.copy()
    if "wind_code" not in df.columns:
        original_index_name = df.index.name
        df = df.reset_index()
        if original_index_name and original_index_name in df.columns:
            df = df.rename(columns={original_index_name: "wind_code"})
        else:
            first_col = df.columns[0]
            df = df.rename(columns={first_col: "wind_code"})

    concept_col = None
    for col in df.columns:
        if col.lower() in {"hotconcept", "hot_concept", "热点概念"}:
            concept_col = col
            break
    if concept_col is None:
        candidates = [col for col in df.columns if col != "wind_code"]
        if not candidates:
            raise ValueError("Cannot find hotconcept column in Wind result.")
        concept_col = candidates[0]

    rows: list[dict[str, object]] = []
    date = _parse_trade_date(trade_date)
    name_map = _build_name_map(names)
    for _, row in df.iterrows():
        wind_code = str(row["wind_code"]).strip()
        raw_value = row[concept_col]
        for concept in split_concepts(raw_value):
            rows.append(
                {
                    "trade_date": date,
                    "wind_code": wind_code,
                    "stock_name": name_map.get(wind_code.upper(), ""),
                    "concept": concept,
                    "raw_value": "" if pd.isna(raw_value) else str(raw_value),
                }
            )

    out = pd.DataFrame(rows, columns=["trade_date", "wind_code", "stock_name", "concept", "raw_value"])
    if not out.empty:
        out = out.drop_duplicates(["trade_date", "wind_code", "concept"]).sort_values(
            ["trade_date", "concept", "wind_code"]
        )
    return out


def _build_name_map(names: pd.DataFrame | dict[str, str] | None) -> dict[str, str]:
    if names is None:
        return {}
    if isinstance(names, dict):
        return {str(k).upper(): "" if pd.isna(v) else str(v) for k, v in names.items()}

    df = names.copy()
    if "wind_code" not in df.columns:
        if df.index.name:
            df = df.reset_index().rename(columns={df.index.name: "wind_code"})
        else:
            df = df.reset_index().rename(columns={df.reset_index().columns[0]: "wind_code"})

    name_col = None
    candidates = ["sec_name", "SEC_NAME", "name", "S_INFO_NAME", "证券简称"]
    for col in candidates:
        if col in df.columns:
            name_col = col
            break
    if name_col is None:
        return {}

    out = {}
    for _, row in df.iterrows():
        code = str(row["wind_code"]).strip().upper()
        value = row[name_col]
        out[code] = "" if pd.isna(value) else str(value)
    return out


def load_stock_hotconcept(
    *,
    root: str | Path | None = None,
    trade_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    path = concept_path(root)
    if not path.exists():
        raise FileNotFoundError(f"Stock concept mapping not found: {path}")
    df = pd.read_parquet(path)
    if "stock_name" not in df.columns:
        df["stock_name"] = ""
    ordered = ["trade_date", "wind_code", "stock_name", "concept", "raw_value"]
    if all(col in df.columns for col in ordered):
        df = df[ordered + [col for col in df.columns if col not in ordered]]
    if trade_date is not None:
        date = pd.to_datetime(trade_date).date().isoformat()
        df = df[df["trade_date"].astype(str) == date]
    return df.reset_index(drop=True)


def _latest_date(df: pd.DataFrame) -> str | None:
    if df.empty or "trade_date" not in df.columns:
        return None
    return str(df["trade_date"].max())


def get_stock_concepts(
    wind_code: str,
    *,
    trade_date: str | pd.Timestamp | None = None,
    root: str | Path | None = None,
    as_list: bool = True,
) -> list[str] | pd.DataFrame:
    df = load_stock_hotconcept(root=root, trade_date=trade_date)
    if trade_date is None:
        latest = _latest_date(df)
        if latest is not None:
            df = df[df["trade_date"].astype(str) == latest]
    out = df[df["wind_code"].astype(str).str.upper() == wind_code.upper()].copy()
    if as_list:
        return sorted(out["concept"].dropna().astype(str).unique().tolist())
    return out.reset_index(drop=True)


def get_concept_constituents(
    concept: str,
    *,
    trade_date: str | pd.Timestamp | None = None,
    root: str | Path | None = None,
    exact: bool = True,
    as_list: bool = False,
) -> list[str] | pd.DataFrame:
    df = load_stock_hotconcept(root=root, trade_date=trade_date)
    if trade_date is None:
        latest = _latest_date(df)
        if latest is not None:
            df = df[df["trade_date"].astype(str) == latest]
    if exact:
        out = df[df["concept"].astype(str) == concept].copy()
    else:
        out = df[df["concept"].astype(str).str.contains(concept, regex=False, na=False)].copy()
    out = out.sort_values(["trade_date", "wind_code", "concept"]).reset_index(drop=True)
    if as_list:
        return sorted(out["wind_code"].dropna().astype(str).unique().tolist())
    return out


def save_stock_hotconcept(
    mapping: pd.DataFrame,
    *,
    raw: pd.DataFrame | None = None,
    root: str | Path | None = None,
    replace_date: bool = True,
) -> Path:
    path = concept_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)

    out = mapping.copy()
    if replace_date and path.exists() and not out.empty:
        old = pd.read_parquet(path)
        dates = set(out["trade_date"].astype(str).unique())
        old = old[~old["trade_date"].astype(str).isin(dates)]
        out = pd.concat([old, out], ignore_index=True)

    if not out.empty:
        out = out.drop_duplicates(["trade_date", "wind_code", "concept"]).sort_values(
            ["trade_date", "concept", "wind_code"]
        )
    out.to_parquet(path, index=False)

    if raw is not None:
        raw_path = raw_concept_path(root)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw.to_parquet(raw_path, index=True)

    return path
