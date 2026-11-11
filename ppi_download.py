"""
Download Producer Price Index (PPI) data from Eurostat via SDMX API.
Downloads three monthly dataflows with NACE Rev.2 classification for
industrial categories:
  - STS_INPP_M:   producer prices in industry, total (indic_bt PRC_PRR)
  - STS_INPPD_M:  producer prices on the domestic market (indic_bt PRC_PRR_DOM)
  - STS_INPPND_M: producer prices on the non-domestic market (indic_bt PRC_PRR_NDOM)
All three flows publish the index (I21), the percentage change on the previous
period (PCH_PRE) and the annual rate of change (PCH_SM). Each flow is saved
as its own Parquet file.
"""

import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import sdmx
from sdmx.exceptions import HTTPError
from tenacity import retry, stop_after_attempt, wait_random_exponential

# ===========================
# CONFIGURATION
# ===========================

OUTPUT_DIR = Path("src", "assets", "data")
MAPS_DIR = Path("src", "assets", "maps")
CATEGORIES_FILE = MAPS_DIR / "nace_r2.csv"

FREQ = "M"
START_PERIOD = "2000-01"

GEO_KEY = "EU27_2020+EA21+EA20+EA19+BE+BG+CZ+DK+DE+EE+IE+EL+ES+FR+HR+IT+CY+LV+LT+LU+HU+MT+NL+AT+PL+PT+RO+SI+SK+FI+SE"
S_ADJ_KEY = "NSA"
UNIT_KEY = "I21+PCH_PRE+PCH_SM"

FLOWS = [
    {
        "dataflow_id": "STS_INPP_M",
        "indic_bt": "PRC_PRR",
        "output_file": OUTPUT_DIR / "ppi_data.parquet",
        "update_file": Path("src", "assets", "ppi_last_update.txt"),
    },
    {
        "dataflow_id": "STS_INPPD_M",
        "indic_bt": "PRC_PRR_DOM",
        "output_file": OUTPUT_DIR / "ppi_domestic_data.parquet",
        "update_file": Path("src", "assets", "ppi_domestic_last_update.txt"),
    },
    {
        "dataflow_id": "STS_INPPND_M",
        "indic_bt": "PRC_PRR_NDOM",
        "output_file": OUTPUT_DIR / "ppi_nondomestic_data.parquet",
        "update_file": Path("src", "assets", "ppi_nondomestic_last_update.txt"),
    },
]


# ===========================
# SDMX CLIENT
# ===========================

client = sdmx.Client("ESTAT")


# ===========================
# DOWNLOAD FUNCTION
# ===========================


@retry(
    stop=stop_after_attempt(7),
    wait=wait_random_exponential(multiplier=1, max=60),
    reraise=True,
)
def download_data(nace_code, dimensions, freq, start_period, dataflow_id, indic_bt):
    """Download data for a specific NACE Rev.2 category and return DataFrame."""

    freq_dim = next(d for d in dimensions if d.id.lower() == "freq")
    geo_dim = next(d for d in dimensions if d.id.lower() == "geo")
    nace_dim = next(d for d in dimensions if "nace" in d.id.lower())
    indic_bt_dim = next((d for d in dimensions if "indic_bt" in d.id.lower()), None)
    s_adj_dim = next((d for d in dimensions if d.id.lower() == "s_adj"), None)
    unit_dim = next((d for d in dimensions if "unit" in d.id.lower()), None)

    key = {
        freq_dim.id: freq,
        nace_dim.id: nace_code,
        geo_dim.id: GEO_KEY,
    }

    if indic_bt_dim:
        key[indic_bt_dim.id] = indic_bt
    if s_adj_dim:
        key[s_adj_dim.id] = S_ADJ_KEY
    if unit_dim:
        key[unit_dim.id] = UNIT_KEY

    try:
        response = client.get(
            resource_type="data",
            resource_id=dataflow_id,
            key=key,
            params={
                "startPeriod": start_period,
            },
        )
    except HTTPError as e:
        resp = e.response
        status = getattr(resp, "status_code", None)
        body = getattr(resp, "text", "")
        # Codes absent from a dataflow dimension (HTTP 400 fault 150) or with
        # no observations at all (HTTP 404) are normal: the NACE map covers
        # more series than some flows publish. Skip them without retrying;
        # any other HTTP error is transient and left to the retry decorator.
        if status == 404 or (status == 400 and "INVALID_QUERY_DIMENSION_VALUE" in body):
            print(f"  Not available in {dataflow_id} for {nace_code}")
            return None
        raise

    data = response.data

    if data is None:
        print(f"  No data found for {nace_code}")
        return None

    df = sdmx.to_pandas(data)

    if df.empty:
        print(f"  Empty dataset for {nace_code}")
        return None

    if df.isnull().all().all():
        print(f"  All-null dataset for {nace_code}")
        return None

    df = df.reset_index()
    print(f"  Downloaded {len(df)} rows for {nace_code}")

    time.sleep(0.3)
    return df


# ===========================
# MAIN
# ===========================


def process_flow(flow, codes_to_download):
    """Download one dataflow for all NACE categories and save it as Parquet."""

    dataflow_id = flow["dataflow_id"]
    print(f"\n=== Dataflow {dataflow_id} (indic_bt {flow['indic_bt']}) ===")

    print("Downloading data structure...")
    try:
        dsd_response = client.get(
            resource_type="datastructure",
            resource_id=dataflow_id,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to download DSD: {e}")

    dsd = dsd_response.structure[dataflow_id]
    dimensions = list(dsd.dimensions.components)
    print(f"  Dimensions: {[d.id for d in dimensions]}")

    all_data = []
    errors = []

    for i, nace_code in enumerate(codes_to_download):
        print(f"\nProcessing {i + 1}/{len(codes_to_download)}: {nace_code}")

        try:
            df = download_data(
                nace_code, dimensions, FREQ, START_PERIOD, dataflow_id, flow["indic_bt"]
            )
            if df is not None:
                all_data.append(df)
        except Exception as e:
            print(f"  Error for {nace_code}: {e}")
            errors.append((nace_code, str(e)))
            continue

    if not all_data and not errors:
        # Every request was skipped as "not available": this means the flow
        # key itself (indic_bt / unit / s_adj) is wrong, not missing series.
        raise RuntimeError(
            f"No data downloaded for {dataflow_id}: all {len(codes_to_download)} "
            "NACE codes were skipped. Check the flow's key values (indic_bt, "
            "s_adj, unit) against the Eurostat datastructure."
        )

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.drop_duplicates(keep="last")
        combined_df = combined_df.drop(columns=["freq"], errors="ignore")

        combined_df.to_parquet(flow["output_file"], index=False)
        print(f"\nSaved {len(combined_df)} rows to {flow['output_file']}")
    else:
        print("\nNo data to process.")

    if errors:
        print(f"\n{len(errors)} errors encountered:")
        for code, err in errors:
            print(f"  {code}: {err}")

    now = datetime.now(ZoneInfo("Europe/Rome"))
    flow["update_file"].write_text(now.strftime("%Y-%m-%d %H:%M %Z"))
    print(f"\nSaved last update date to {flow['update_file']}")

    return errors


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not CATEGORIES_FILE.exists():
        raise FileNotFoundError(
            f"NACE R2 categories file not found: {CATEGORIES_FILE}\n"
            "Download it from: https://github.com/paluigi-moltis/ppi_eurostat/blob/main/nace_r2.csv"
        )

    print("Loading NACE R2 categories...")
    code_map = pd.read_csv(CATEGORIES_FILE)

    codes_to_download = code_map["code"].tolist()
    print(f"  {len(codes_to_download)} categories to download")

    all_errors = {}

    for flow in FLOWS:
        all_errors[flow["dataflow_id"]] = process_flow(flow, codes_to_download)

    total_errors = sum(len(e) for e in all_errors.values())
    if total_errors:
        print(f"\n{total_errors} errors across {len(FLOWS)} dataflows")

    print("\nAll processing complete.")


if __name__ == "__main__":
    main()
