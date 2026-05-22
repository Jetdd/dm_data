# dm-data

Local reader API for `E:\dm_intraday`.

```python
import dm_data as dm

df = dm.get_price(
    asset="bond",
    code="2500006.IB",
    frequency="1m",
    start_date="2026-05-01",
    end_date="2026-05-22",
)

df = dm.bond.get_price("2500006.IB", frequency="1m")
df = dm.stock.get_price("000001.SZ", frequency="1m")
```

Stock hot concept mapping:

```python
dm.get_stock_concepts("000001.SZ")
dm.get_concept_constituents("机器人概念")
dm.get_concept_constituents("机器人", exact=False, as_list=True)
```

Update the mapping from Wind:

```powershell
D:\Miniforge\envs\downgrade\python.exe C:\Users\huawei\dm_intraday_api\scripts\fetch_wind_hotconcept.py --date 2026-05-22 --trade-date 2026-05-21
```

Default root is `E:\dm_intraday`. Override with:

```powershell
$env:DM_INTRADAY_ROOT="E:\dm_intraday"
```
