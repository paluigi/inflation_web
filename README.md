# Eurostat Inflation Dashboard

## Overview

A web-based dashboard for exploring Euro Area inflation data from Eurostat:

- **HICP**: Harmonized Index of Consumer Prices
- **HICP Weights**: Item weights for HICP (annual)
- **PPI**: Producer Price Index

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

- Downloads Producer Price Index monthly data (STS_INPP_M)
- Output: `src/assets/data/ppi_data.parquet`
- Last update: `src/assets/ppi_last_update.txt`

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
| `ppi_data.parquet` | Producer Price Index data |

## Map Files

| File | Description |
|------|-------------|
| `coicop18.csv` | COICOP classification codes |
| `nace_r2.csv` | NACE Rev.2 classification codes |
| `geo.csv` / `geo_ppi.csv` | Geography codes |
| `unit.csv` / `unit_ppi.csv` | Unit of measurement codes |