"""
Run once locally to generate cached parquet files.

Requires:
    COPERNICUSMARINE_SERVICE_USERNAME
    COPERNICUSMARINE_SERVICE_PASSWORD
"""

import os
import copernicusmarine
import xarray as xr
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

BBOX = dict(
    minimum_longitude=-30,
    maximum_longitude=5,
    minimum_latitude=35,
    maximum_latitude=65,
)
def fetch_and_save(
    dataset_id: str,
    variable: str,
    out_path: Path,
    username: str,
    password: str,
    start_datetime: str,
    end_datetime: str,
    **extra,
) -> None:
    print(f"Fetching {variable} from {dataset_id} ({start_datetime} → {end_datetime}) …")
    ds = copernicusmarine.open_dataset(
        dataset_id=dataset_id,
        variables=[variable],
        username=username,
        password=password,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        **BBOX,
        **extra,
    )
    ds = ds.isel(latitude=slice(None, None, 2), longitude=slice(None, None, 2))
    da = ds[variable]

    # Squeeze depth dim if present
    if "depth" in da.dims:
        da = da.isel(depth=0)

    df = (
        da.to_dataframe()
        .reset_index()
        .rename(columns={variable: "value"})
        [["latitude", "longitude", "time", "value"]]
        .rename(columns={"latitude": "lat", "longitude": "lon"})
        .dropna(subset=["value"])
    )
    df["time"] = pd.to_datetime(df["time"])
    df.to_parquet(out_path, index=False)
    print(f"  → saved {len(df):,} rows to {out_path}")


def main() -> None:
    username = os.environ["COPERNICUSMARINE_SERVICE_USERNAME"]
    password = os.environ["COPERNICUSMARINE_SERVICE_PASSWORD"]

    fetch_and_save(
        dataset_id="cmems_mod_glo_phy_my_0.083deg_P1M-m",
        variable="thetao",
        out_path=DATA_DIR / "sst_monthly.parquet",
        username=username,
        password=password,
        start_datetime="2000-01-01",
        end_datetime="2023-12-31",
    )
    fetch_and_save(
        dataset_id="cmems_mod_glo_bgc_my_0.25deg_P1M-m",
        variable="chl",
        out_path=DATA_DIR / "chl_monthly.parquet",
        username=username,
        password=password,
        start_datetime="2018-01-01",
        end_datetime="2023-12-31",
    )


if __name__ == "__main__":
    main()
