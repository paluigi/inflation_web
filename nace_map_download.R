library(hicp)
library(dplyr)
library(tidyr)

fil <- datafilters("sts_inpp_m")

print(paste("Total rows:", nrow(fil)))
print(paste("Unique concepts:", paste(unique(fil$concept), collapse = ", ")))

nace_col <- fil |> filter(grepl("nace", concept, ignore.case = TRUE))

if (nrow(nace_col) == 0) {
  nace_col <- fil |> filter(concept == "nace_r2")
}

if (nrow(nace_col) == 0) {
  print("Could not find NACE concept. Available concepts:")
  print(unique(fil$concept))
  stop("No NACE concept found")
}

print(paste("NACE rows:", nrow(nace_col)))

codes <- nace_col |>
  mutate(level = level(code)) |>
  mutate(parent = as.character(parent(code))) |>
  mutate(level = replace_na(level, 0))

print(paste("Unique NACE codes:", length(unique(codes$code))))

write.csv(codes, file = "src/assets/maps/nace_r2.csv", row.names = FALSE)
print("Saved NACE R2 map to src/assets/maps/nace_r2.csv")

ppi_geo_codes <- c("EU27_2020", "EA21", "EA20", "EA19",
                   "BE", "BG", "CZ", "DK", "DE", "EE",
                   "IE", "EL", "ES", "FR", "HR", "IT",
                   "CY", "LV", "LT", "LU", "HU", "MT",
                   "NL", "AT", "PL", "PT", "RO", "SI",
                   "SK", "FI", "SE")

geo_col <- fil |>
  filter(concept == "geo") |>
  filter(code %in% ppi_geo_codes)

print(paste("PPI geo codes:", nrow(geo_col)))

write.csv(geo_col, file = "src/assets/maps/geo_ppi.csv", row.names = FALSE)
print("Saved PPI geo map to src/assets/maps/geo_ppi.csv")

ppi_unit_codes <- c("I21", "PCH_PRE")

unit_col <- fil |>
  filter(concept == "unit") |>
  filter(code %in% ppi_unit_codes)

print(paste("PPI unit codes:", nrow(unit_col)))

write.csv(unit_col, file = "src/assets/maps/unit_ppi.csv", row.names = FALSE)
print("Saved PPI unit map to src/assets/maps/unit_ppi.csv")

print("Done!")
