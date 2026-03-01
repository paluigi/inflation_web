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

@retry(stop=stop_after_attempt(7),wait= wait_random_exponential(multiplier=1, max=60), reraise=True)
def download_data(item_id, dimensions, FREQ, START_PERIOD, DATAFLOW_ID, OUTPUT_DIR):
    """Download data for a specific ECOICOPv2 item and save to CSV."""
    
    geo_key = "EU+EA+BE+BG+CZ+DK+DE+EE+IE+EL+ES+FR+HR+IT+CY+LV+LT+LU+HU+MT+NL+AT+PL+PT+RO+SI+SK+FI+SE"
    unit_key = "I25+RCH_A+RCH_M"
    # Detect dimensions
    freq_dim = next(d for d in dimensions if d.id.lower() == "freq")
    geo_dim = next(d for d in dimensions if d.id.lower() == "geo")
    item_dim = next(d for d in dimensions if "coicop" in d.id.lower())
    unit_dim = next((d for d in dimensions if "unit" in d.id.lower()), None)  # Optional

    key = {
        freq_dim.id: FREQ,
        item_dim.id: item_id,
        geo_dim.id: geo_key,
        unit_dim.id: unit_key
    }

    response = client.get(
        resource_type="data",
        resource_id=DATAFLOW_ID,
        key=key,
        params={
            "startPeriod": START_PERIOD
        }
    )

    data = response.data

    if data is None:
        print("No data found.")
        return False

    df = sdmx.to_pandas(data)

    if df.empty:
        print("Empty dataset.")
        return False

    df = df.reset_index()

    output_file = OUTPUT_DIR / f"{item_id}.csv"
    df.to_csv(output_file, index=False)
    print(f"Saved {output_file}")

    time.sleep(0.3)


# ===========================
# CONFIGURATION
# ===========================

DATAFLOW_ID = "PRC_HICP_MINR"
OUTPUT_DIR = Path("src", "assets", "data")
MAPS_DIR = Path("src", "assets", "maps")
OUTPUT_DIR.mkdir(exist_ok=True)

FREQ = "M"
START_PERIOD = "2000-01"

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
    dsd_response = client.get(
        resource_type="datastructure",
        resource_id=DATAFLOW_ID
    )
except Exception as e:
    raise RuntimeError(f"Failed to download DSD: {e}")

dsd = dsd_response.structure[DATAFLOW_ID]

dimensions = list(dsd.dimensions.components)

# ===========================
# DOWNLOAD LOOP
# ===========================

for i, item_id in enumerate(code_map["code"]):
    print(f"\nProcessing item {i+1}/{len(code_map['code'])}: {item_id}")

    try:
        download_data(item_id, dimensions, FREQ, START_PERIOD, DATAFLOW_ID, OUTPUT_DIR)

    except Exception as e:
        print(f"Error for item {item_id}: {e}")
        continue

print("\nDone.")

# ===========================
# GEO-BASED FILE GENERATION
# ===========================

geo_list = ["EU", "EA", "BE", "BG", "CZ", "DK", "DE", "EE", "IE", "EL", "ES", "FR", "HR", "IT", "CY", "LV", "LT", "LU", "HU", "MT", "NL", "AT", "PL", "PT", "RO", "SI", "SK", "FI", "SE"]

print("\nGenerating geo-based files...")

all_data = []
for item_file in OUTPUT_DIR.glob("*.csv"):
    df = pd.read_csv(item_file)
    all_data.append(df)

if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.drop_duplicates(keep="last")

    for geo in geo_list:
        geo_df = combined_df[combined_df["geo"] == geo]
        if not geo_df.empty:
            output_file = OUTPUT_DIR / f"{geo}.csv"
            geo_df.to_csv(output_file, index=False)
            print(f"Saved {output_file}")
        else:
            print(f"No data for geo: {geo}")
else:
    print("No data to process for geo-based files.")

# ===========================
# SAVE LAST UPDATE DATE
# ===========================
update_file = Path("src", "assets", "last_update.txt")
# use Rome timezone to get CET/CEST depending on date
now = datetime.now(ZoneInfo("Europe/Rome"))
# include timezone abbreviation in string
update_file.write_text(now.strftime("%Y-%m-%d %H:%M %Z"))
print(f"Saved last update date to {update_file}")

print("\nAll processing complete.")
