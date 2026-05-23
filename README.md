# dm-data

Unified data access layer for **DM intraday bars**, **RiceQuant futures**, and **hot-concept mappings**.

## Supported frequencies (DM)

`1m` `5m` `15m` `30m` `60m` `1d` `1w` `1mo`

Aliases: `1min` `day` `daily` `d` `week` `weekly` `w` `month` `monthly` `mo` ...

## Quick start

```python
import dm_data as dm

# DM local intraday bars (auto-fetch from DM if missing locally)
df = dm.get_price(
    asset="bond",
    code="2500006.IB",
    frequency="1m",
    start_date="2026-05-01",
    end_date="2026-05-22",
)

# DM daily bars
df = dm.get_price(asset="stock", code="000001.SZ", frequency="1d", start_date="2024-01-01")

# Bond / stock shorthands
df = dm.bond.get_price("2500006.IB", frequency="1m")
df = dm.stock.get_price("000001.SZ", frequency="1m")

# Hot-concept mappings
concepts = dm.get_stock_concepts("000001.SZ")
constituents = dm.get_concept_constituents("机器人概念", exact=True, as_list=True)
```

## RiceQuant futures (requires `rqdatac`)

```python
# IM 中证1000 主力合约前复权日线
df = dm.futures.get_dominant_price(
    "IM",
    start_date="2024-01-01",
    end_date="2024-12-31",
    frequency="1d",
    adjust_type="pre",
)

# 1-minute dominant continuous (pre-adjusted)
df = dm.futures.get_dominant_price("IM", frequency="1m", start_date="2024-06-01")

# Specific contract
df = dm.futures.get_price("IM2506.CCFX", start_date="2024-01-01", frequency="1d")

# Member rank, basis, margin, warehouse stocks ...
df = dm.futures.get_member_rank("IM2506.CCFX", trading_date="2024-06-21")
df = dm.futures.get_basis("IM2506.CCFX", start_date="2024-01-01", frequency="1d")
df = dm.futures.get_commission_margin(["IM2506.CCFX"])
```

## Configuration

Set environment variables so credentials never appear in code:

```powershell
# DM
$env:INNO_APP_KEY="your_key"
$env:INNO_SM4_KEY="your_secret"

# RiceQuant
$env:RQDATAC_USER="your_rq_username"
$env:RQDATAC_PASSWORD="your_rq_password"

# Local data root (optional, default E:\dm_intraday)
$env:DM_INTRADAY_ROOT="E:\dm_intraday"
```

Or use `dm.get_config()` programmatically:

```python
from dm_data import get_config
cfg = get_config()
cfg.init_rqdatac()          # manual RiceQuant init
client = cfg.dm_client()    # manual DMQuantApiClient
```

## Default root

Default local parquet root is `E:\dm_intraday`. Override with:

```powershell
$env:DM_INTRADAY_ROOT="E:\dm_intraday"
```

Or in Python:

```python
dm.set_root(r"E:\dm_intraday")
```
