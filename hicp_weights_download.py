import sdmx
import pandas as pd
import time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from tenacity import retry, stop_after_attempt, wait_random_exponential

# ===========================
# DOWNLOAD FUNCTION
# ===========================


@retry(
    stop=stop_after_attempt(7),
    wait=wait_random_exponential(multiplier=1, max=60),
    reraise=True,
)
def download_data(item_id, dimensions, FREQ, START_PERIOD, DATAFLOW_ID):
    """Download yearly weight data for a specific ECOICOPv2 item and return DataFrame."""

    geo_key = "EU+EA+BE+BG+CZ+DK+DE+EE+IE+EL+ES+FR+HR+IT+CY+LV+LT+LU+HU+MT+NL+AT+PL+PT+RO+SI+SK+FI+SE"
    unit_key = "PER_THS_TOT"

    freq_dim = next(d for d in dimensions if d.id.lower() == "freq")
    geo_dim = next(d for d in dimensions if d.id.lower() == "geo")
    item_dim = next(d for d in dimensions if "coicop" in d.id.lower())
    unit_dim = next((d for d in dimensions if "unit" in d.id.lower()), None)

    key = {
        freq_dim.id: FREQ,
        item_dim.id: item_id,
        geo_dim.id: geo_key,
    }

    if unit_dim:
        key[unit_dim.id] = unit_key

    response = client.get(
        resource_type="data",
        resource_id=DATAFLOW_ID,
        key=key,
        params={"startPeriod": START_PERIOD},
    )

    data = response.data

    if data is None:
        print(f"No data found for {item_id}.")
        return None

    df = sdmx.to_pandas(data)

    if df.empty:
        print(f"Empty dataset for {item_id}.")
        return None

    df = df.reset_index()
    print(f"Downloaded weight data for {item_id}")

    time.sleep(0.3)
    return df


# ===========================
# CONFIGURATION
# ===========================

DATAFLOW_ID = "PRC_HICP_IW"
OUTPUT_DIR = Path("src", "assets", "data")
MAPS_DIR = Path("src", "assets", "maps")
OUTPUT_DIR.mkdir(exist_ok=True)

FREQ = "A"
START_PERIOD = "2000"

# ===========================
# SDMX CLIENT
# ===========================

client = sdmx.Client("ESTAT")

# ===========================
# LOAD DATA MAPS
# ===========================

code_map = pd.read_csv(MAPS_DIR / "coicop18.csv")

# ===========================
# GET STRUCTURE
# ===========================

print("Downloading data structure...")

try:
    dsd_response = client.get(resource_type="datastructure", resource_id=DATAFLOW_ID)
except Exception as e:
    raise RuntimeError(f"Failed to download DSD: {e}")

dsd = dsd_response.structure[DATAFLOW_ID]

dimensions = list(dsd.dimensions.components)

# ===========================
# DOWNLOAD LOOP
# ===========================

all_data = []
for i, item_id in enumerate(code_map["code"]):
    print(f"\nProcessing item {i + 1}/{len(code_map['code'])}: {item_id}")

    try:
        df = download_data(item_id, dimensions, FREQ, START_PERIOD, DATAFLOW_ID)
        if df is not None:
            all_data.append(df)

    except Exception as e:
        print(f"Error for item {item_id}: {e}")
        continue

# ===========================
# SAVE TO PARQUET
# ===========================

if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.drop_duplicates(keep="last")
    combined_df = combined_df.drop(columns=["freq"], errors="ignore")

    output_file = OUTPUT_DIR / "hicp_weights.parquet"
    combined_df.to_parquet(output_file, index=False)
    print(f"\nSaved {output_file}")
else:
    print("No data to process.")

# ===========================
# SAVE LAST UPDATE DATE
# ===========================
update_file = Path("src", "assets", "weights_last_update.txt")
now = datetime.now(ZoneInfo("Europe/Rome"))
update_file.write_text(now.strftime("%Y-%m-%d %H:%M %Z"))
print(f"Saved last update date to {update_file}")

print("\nAll processing complete.")
