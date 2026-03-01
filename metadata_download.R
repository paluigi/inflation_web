library(hicp)
library(dplyr)
library(tidyr)

fil <- datafilters("prc_hicp_minr")

fil |> filter(concept == "unit") |> filter(code %in% c("I25", "RCH_M", "RCH_A")) |> write.csv(file = "src/assets/maps/unit.csv", row.names = FALSE)
fil |> filter(concept == "geo") |> filter(code %in% c("EU", "EA", "BE", "BG", "CZ", "DK", "DE", "EE",
                                               "IE", "EL", "ES", "FR", "HR", "IT",
                                               "CY", "LV", "LT", "LU", "HU", "MT",
                                               "NL", "AT", "PL", "PT", "RO", "SI",
                                               "SK", "FI", "SE")) |> write.csv(file = "src/assets/maps/geo.csv", row.names = FALSE)
  

codes <- fil |> filter(concept == "coicop18") |> mutate(level=level(code))|> mutate (parent=as.character(parent(code))) |> mutate(level=replace_na(level, 0))

write.csv(codes, file = "src/assets/maps/coicop18.csv", row.names = FALSE)


dtd <- datasets()
dtf <- datafilters(id="prc_hicp_iw")
dtf

dtf_c <- datafilters(id="prc_hicp_cw")
dtf_c

dtf_ctr <- datafilters(id="prc_hicp_ctr")
dtf_ctr

# unique(codes$level)
# unique(fil$concept)


# code_list = c("TOTAL", "CP01", "CP011", "CP0111", "CP01111", "CP01112", "CP01113", "CP011131", "CP011139", "CP01114", "CP01115", "CP01119", 
#               "CP0112", "CP01121", "CP01122", "CP011222", "CP01223", "CP011224", "CP011225", "CP011226", "CP011227", "CP011229", "CP01123", 
#               "CP01124", "CP01125", "CP0113", "CP01131", "CP01132", "CP01133", "CP01134", "CP01135", "CP01136", "CP01137", "CP0114", "CP01141", 
#               "CP01142", "CP01143", "CP01144", "CP01145", "CP01146", "CP01147", "CP01148", "CP01149", "CP0115", "CP01151", "CP011513", "CP01152", 
#               "CP01153", "CP01159", "CP0116", "CP01161", "CP01162", "CP01163", "CP01164", "CP01165", "CP01166", "CP01167", "CP01168", "CP01169", 
#               "CP0117", "CP01171", "CP01172", "CP01173", "CP01174", "CP01175", "CP011751", "CP01176", "CP01177", "CP01178", "CP01179", "CP0118", 
#               "CP01181", "CP01182", "CP01183", "CP01184", "CP01185", "CP01186", "CP01189", "CP0119", "CP01191", "CP01192", "CP01193", "CP01194", 
#               "CP01199", "CP012", "CP0121", "CP01210", "CP0122", "CP01220", "CP0123", "CP01230", "CP0124", "CP01240", "CP0125", "CP01250", "CP0126", 
#               "CP01260", "CP0129", "CP01290", "CP013", "CP0130", "CP01300", "CP02", "CP021", "CP0211", "CP02110", "CP0212", "CP02121", "CP02122", 
#               "CP0213", "CP02130", "CP0219", "CP02190", "CP022", "CP0220", "CP02200", "CP023", "CP0230", "CP02301", "CP02302", "CP02309", "CP03", 
#               "CP031", "CP0311", "CP03110", "CP0312", "CP03121", "CP03122", "CP03123", "CP03124", "CP0313", "CP03131", "CP03132", "CP0314", "CP03141", 
#               "CP03142", "CP032", "CP0321", "CP03211", "CP03212", "CP03213", "CP0322", "CP03220", "CP04", "CP041", "CP0411", "CP04110", "CP0412", 
#               "CP04121", "CP04122", "CP043", "CP0431", "CP04311", "CP04312", "CP0432", "CP04320", "CP044", "CP0441", "CP04411", "CP04412", "CP0442", 
#               "CP04420", "CP0443", "CP04431", "CP04432", "CP0444", "CP04441", "CP04449", "CP045", "CP0451", "CP04510", "CP0452", "CP04521", "CP04522", 
#               "CP0453", "CP04530", "CP0454", "CP04541", "CP04542", "CP04543", "CP04549", "CP0455", "CP04550", "CP05", "CP051", "CP0511", "CP05111", 
#               "CP05112", "CP05113", "CP05114", "CP0512", "CP05120", "CP052", "CP0521", "CP05211", "CP05212", "CP05213", "CP05219", "CP0522", "CP05220", 
#               "CP053", "CP0531", "CP05311", "CP05312", "CP05313", "CP05314", "CP05319", "CP0532", "CP05321", "CP05322", "CP05329", "CP0533", "CP05330", 
#               "CP054", "CP0540", "CP05401", "CP05402", "CP05403", "CP05404", "CP055", "CP0551", "CP05510", "CP0552", "CP05521", "CP05522", "CP0553", 
#               "CP05530", "CP056", "CP0561", "CP05611", "CP05619", "CP0562", "CP05621", "CP05629", "CP06", "CP061", "CP0611", "CP06111", "CP06112", 
#               "CP0612", "CP06121", "CP06122", "CP06123", "CP0613", "CP06131", "CP06132", "CP06133", "CP0614", "CP06140", "CP062", "CP0621", "CP06211", 
#               "CP06219", "CP0622", "CP06221", "CP06229", "CP0623", "CP06231", "CP06232", "CP063", "CP0631", "CP06310", "CP0632", "CP06320", "CP064", 
#               "CP0641", "CP06410", "CP0642", "CP06420", "CP07", "CP071", "CP0711", "CP07111", "CP07112", "CP0712", "CP07120", "CP0713", "CP07130", 
#               "CP0714", "CP07140", "CP072", "CP0721", "CP07211", "CP07212", "CP07213", "CP0722", "CP07221", "CP07222", "CP07223", "CP07224", "CP0723", 
#               "CP07230", "CP0724", "CP07241", "CP07242", "CP07243", "CP07244", "CP073", "CP0731", "CP07311", "CP07312", "CP0732", "CP07321", "CP07322", 
#               "CP07323", "CP07329", "CP0733", "CP07331", "CP07332", "CP0734", "CP07340", "CP0735", "CP07350", "CP0736", "CP07360", "CP074", "CP0741", 
#               "CP07411", "CP07412", "CP0749", "CP07491", "CP07492", "CP08", "CP081", "CP0811", "CP08110", "CP0812", "CP08120", "CP0813", "CP08131", 
#               "CP08132", "CP0814", "CP08140", "CP0815", "CP08150", "CP0819", "CP08191", "CP08192", "CP082", "CP0820", "CP08200", "CP083", "CP0831", 
#               "CP08310", "CP0832", "CP08320", "CP0833", "CP08330", "CP0834", "CP08340", "CP0835", "CP08350", "CP0839", "CP08391", "CP08392", "CP08399", 
#               "CP09", "CP091", "CP0911", "CP09111", "CP09112", "CP09113", "CP0912", "CP09121", "CP09122", "CP09123", "CP09124", "CP09129", "CP092", 
#               "CP0921", "CP09211", "CP09212", "CP09213", "CP0922", "CP09221", "CP09222", "CP093", "CP0931", "CP09311", "CP09312", "CP0932", "CP09321", 
#               "CP09322", "CP094", "CP0941", "CP09410", "CP0942", "CP09421", "CP09422", "CP0943", "CP09431", "CP09432", "CP0944", "CP09440", "CP0945", 
#               "CP09450", "CP0946", "CP09461", "CP09462", "CP09463", "CP0947", "CP09470", "CP095", "CP0951", "CP09510", "CP0952", "CP09520", "CP096", 
#               "CP0961", "CP09610", "CP0962", "CP09620", "CP0963", "CP09630", "CP0969", "CP09690", "CP097", "CP0971", "CP09711", "CP09719", "CP0972", 
#               "CP09721", "CP09722", "CP0973", "CP09730", "CP0974", "CP09740", "CP098", "CP0980", "CP09800", "CP10", "CP101", "CP1010", "CP10101", 
#               "CP10102", "CP102", "CP1020", "CP10200", "CP103", "CP1030", "CP10300", "CP104", "CP1040", "CP10400", "CP105", "CP1050", "CP10501", 
#               "CP10509", "CP11", "CP111", "CP1111", "CP11111", "CP11112", "CP1112", "CP11121", "CP11129", "CP112", "CP1120", "CP11201", "CP11202", 
#               "CP11203", "CP11209", "CP12", "CP121", "CP1211", "CP12110", "CP1212", "CP12120", "CP1213", "CP12130", "CP1214", "CP12141", "CP12142", 
#               "CP1219", "CP12190", "CP122", "CP1222", "CP12220", "CP1229", "CP12291", "CP12299", "CP13", "CP131", "CP1311", "CP13111", "CP13112", 
#               "CP1312", "CP13120", "CP1313", "CP13131", "CP13132", "CP132", "CP1321", "CP13211", "CP13212", "CP1322", "CP13220", "CP1329", "CP13291", 
#               "CP13292", "CP133", "CP1330", "CP13301", "CP13302", "CP13303", "CP13309", "CP139", "CP1390", "CP13902", "CP13909", "GD", "FOOD", "FOOD_P", 
#               "FOOD_P_X_TBC", "FOOD_P_X_ALC_TBC", "FOOD_NP", "FOOD_S", "IGD", "IGD_NNRG", "IGD_NNRG_D", "IGD_NNRG_SD", "IGD_NNRG_ND", "NRG", "ELC_GAS", 
#               "FUEL", "SERV", "SERV_COM", "SERV_HOUS", "SERV_MSC", "SERV_REC", "SERV_REC_X_HOA", "SERV_REC_HOA", "SERV_TRA", "NRG_FOOD_NP", "NRG_FOOD_S", 
#               "EDUC_HLTH_SPR", "FROOPP", "TOT_X_FOOD_S", "TOT_X_ALC_TBC", "TOT_X_TBC", "TOT_X_NRG", "TOT_X_NRG_FOOD", "TOT_X_NRG_FOOD_NP", "TOT_X_NRG_FOOD_S", 
#               "TOT_X_FUEL", "TOT_X_HOUS", "TOT_X_EDUC_HLTH_SPR", "TOT_X_FROOPP")

# for (cod in code_list) {
#   print(cod)
#   ecoicop_data <- data("prc_hicp_minr", 
#                       filters = list("unit" = c("I25", "RCH_M", "RCH_A"), 
#                                      "geo" = c("EU", "EA",
#                                                "BE", "BG", "CZ", "DK", "DE", "EE",
#                                                "IE", "EL", "ES", "FR", "HR", "IT",
#                                                "CY", "LV", "LT", "LU", "HU", "MT",
#                                                "NL", "AT", "PL", "PT", "RO", "SI",
#                                                "SK", "FI", "SE"),
#                                      "coicop18" = c(cod)),
#                       date.range = c("2000-01", NA),
#                       verbose = T)
  
#   write.csv(ecoicop_data, file = paste0("r_data/", cod, ".csv"), row.names = FALSE)
#   Sys.sleep(1)
# }

