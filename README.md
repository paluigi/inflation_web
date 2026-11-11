# Eurostat Inflation Dashboard

## Overview

A web-based dashboard for exploring Euro Area inflation data from Eurostat:

- **HICP**: Harmonized Index of Consumer Prices
- **HICP Weights**: Item weights for HICP (annual)
- **PPI**: Producer Price Index — total, domestic market and non-domestic market

Data is fetched from Eurostat's SDMX API and stored as Parquet files for efficient in-browser querying.

## Running the App

Serve the `src/` directory with any HTTP server:

```bash
# Python
python -m http.server 8000

# Node.js
npx serve src

# Or open index.html directly in a browser (some features may require a server)
```

Navigate to `http://localhost:8000` to use the dashboard.

## Updating Data

### Prerequisites

- Python 3.11+ with dependencies: `pip install sdmx pandas tenacity`
- R with packages: `install.packages(c("hicp", "dplyr", "tidyr"))`

### Download Data Files

#### 1. HICP Data (Python)

```bash
python hicp_download.py
```

- Downloads HICP monthly data from Eurostat (PRC_HICP_MINR)
- Output: `src/assets/data/hicp_data.parquet`
- Last update: `src/assets/last_update.txt`

**Flash-estimate release window (day 28–8):** When the script runs between the 28th of the current month and the 8th of the following month, only a limited set of indices is automatically downloaded — the headline total (COICOP level 1) and the main analytical aggregates (COICOP level 0, e.g. energy, food, services, core inflation measures). During this window Eurostat publishes only the HICP flash estimate, so the detailed sub-items (levels 2–6) are not yet updated and polling them is unnecessary. Outside this window all items are downloaded as normal.

#### 2. HICP Weights (Python)

```bash
python hicp_weights_download.py
```

- Downloads yearly weight data (PRC_HICP_IW)
- Output: `src/assets/data/hicp_weights.parquet`
- Last update: `src/assets/weights_last_update.txt`

#### 3. PPI Data (Python)

```bash
python ppi_download.py
```

- Downloads Producer Price Index monthly data from three Eurostat dataflows, for the full NACE Rev.2 classification and all units published by Eurostat (index `I21`, monthly rate `PCH_PRE`, annual rate `PCH_SM`):
  - `STS_INPP_M` (total industry, indic_bt `PRC_PRR`) → `src/assets/data/ppi_data.parquet`, last update: `src/assets/ppi_last_update.txt`
  - `STS_INPPD_M` (domestic market, indic_bt `PRC_PRR_DOM`) → `src/assets/data/ppi_domestic_data.parquet`, last update: `src/assets/ppi_domestic_last_update.txt`
  - `STS_INPPND_M` (non-domestic market, headline indic_bt `PRC_PRR_NDOM`) → `src/assets/data/ppi_nondomestic_data.parquet`, last update: `src/assets/ppi_nondomestic_last_update.txt`
- NACE codes not covered by a flow (e.g. some aggregates are absent from the domestic/non-domestic dataflows) are skipped automatically, so the error list at the end of a run only contains real failures.

### Download Map Files (R)

#### 4. NACE & PPI Maps (R)

```bash
Rscript nace_map_download.R
```

- Downloads NACE Rev.2 classification for PPI
- Outputs: `src/assets/maps/nace_r2.csv`, `geo_ppi.csv`, `unit_ppi.csv`

#### 5. HICP Maps (R)

```bash
Rscript metadata_download.R
```

- Downloads COICOP, geography, and unit mappings for HICP
- Outputs: `src/assets/maps/coicop18.csv`, `geo.csv`, `unit.csv`

## Data Files

| File | Description |
|------|-------------|
| `hicp_data.parquet` | HICP monthly inflation data |
| `hicp_weights.parquet` | HICP annual weights |
| `ppi_data.parquet` | Producer Price Index data — total industry |
| `ppi_domestic_data.parquet` | Producer Price Index data — domestic market |
| `ppi_nondomestic_data.parquet` | Producer Price Index data — non-domestic market |

## Map Files

| File | Description |
|------|-------------|
| `coicop18.csv` | COICOP classification codes |
| `nace_r2.csv` | NACE Rev.2 classification codes |
| `geo.csv` / `geo_ppi.csv` | Geography codes |
| `unit.csv` / `unit_ppi.csv` | Unit of measurement codes |

## Change Log

### 2026-11-11 — Domestic & non-domestic PPI pages

- `ppi_download.py` now downloads three Eurostat dataflows instead of one: `STS_INPP_M` (total, as before), `STS_INPPD_M` (domestic market) and `STS_INPPND_M` (non-domestic market), each into its own Parquet file and last-update stamp. The unit key is extended to `I21+PCH_PRE+PCH_SM`: Eurostat publishes the annual rate of change (`PCH_SM`) for all three flows, so no rate has to be computed locally.
- Two new dashboard pages (`ppi_domestic.html`, `ppi_nondomestic.html`) linked from the "More ▾" navigation dropdown, sharing the existing PPI dictionaries (`geo_ppi.csv`, `nace_r2.csv`, `unit_ppi.csv` — the latter now includes `PCH_SM`).
- NACE codes not available in a dataflow are detected from Eurostat's `INVALID_QUERY_DIMENSION_VALUE` / 404 responses and skipped without retrying; a run that skips *every* code still fails loudly, which guards against a misconfigured flow key.

### 2026-08-04 — Flash-estimate release window filter

- `hicp_download.py` now checks the calendar day of the month at startup. If the script runs between the **28th of the current month and the 8th of the following month** (inclusive), only COICOP level 0 (analytical aggregates) and level 1 (headline total) items are downloaded. During this window Eurostat publishes only the HICP flash estimate; the detailed sub-items (levels 2–6) are not yet updated, so polling them wastes API calls. Outside this window all items are downloaded as before.
- README updated to document the new behavior.


### 2026-07-16 — Fix Excel export floating-point precision

- Numeric values in exported `.xlsx` files are now rounded to exactly 2 decimal places (`Math.round((val + Number.EPSILON) * 100) / 100`), eliminating IEEE 754 artifacts (e.g. `2.3400000000000003`) that broke downstream analysis.
- Refactored the duplicated export logic across HICP, PPI, and Weights pages into a single shared `exportToExcel()` helper in `common.js`.
