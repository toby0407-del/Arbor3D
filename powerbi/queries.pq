// Create a Text parameter named AnalyticsFolder, then create each named query separately.

// Query: DimTree
let
  Raw = Csv.Document(File.Contents(AnalyticsFolder & "/DimTree.csv"), [Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
  Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars=true]),
  Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
  Typed = Table.TransformColumnTypes(Nulls, {{"tree_key", type text}, {"site_id", type text}, {"persistent_tree_id", type text}, {"identity_status", type text}, {"dataset_kind", type text}}, "en-US")
in Typed

// Query: DimScan
let
  Raw = Csv.Document(File.Contents(AnalyticsFolder & "/DimScan.csv"), [Delimiter=",", Columns=7, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
  Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars=true]),
  Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
  Typed = Table.TransformColumnTypes(Nulls, {{"scan_key", type text}, {"site_id", type text}, {"scan_id", type text}, {"observed_at", type date}, {"source_file", type text}, {"source_sha256", type text}, {"dataset_kind", type text}}, "en-US")
in Typed

// Query: FactObservation
let
  Raw = Csv.Document(File.Contents(AnalyticsFolder & "/FactObservation.csv"), [Delimiter=",", Columns=24, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
  Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars=true]),
  Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
  Typed = Table.TransformColumnTypes(Nulls, {{"observation_key", type text}, {"tree_key", type text}, {"scan_key", type text}, {"local_tree_id", type text}, {"observed_at", type date}, {"auto_dbh_cm", type number}, {"auto_source", type text}, {"auto_method", type text}, {"strict_13m", type logical}, {"manual_dbh_cm", type number}, {"manual_source", type text}, {"manual_measured_at", type date}, {"manual_height_m", type number}, {"manual_strict_13m", type logical}, {"comparison_status", type text}, {"error_cm", type number}, {"absolute_error_cm", type number}, {"squared_error_cm2", type number}, {"ape_pct", type number}, {"yolo_confidence", type number}, {"arc_coverage_deg", type number}, {"review_required", type logical}, {"review_reason", type text}, {"dataset_kind", type text}}, "en-US")
in Typed

// Query: FactEstimate
let
  Raw = Csv.Document(File.Contents(AnalyticsFolder & "/FactEstimate.csv"), [Delimiter=",", Columns=13, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
  Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars=true]),
  Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
  Typed = Table.TransformColumnTypes(Nulls, {{"observation_key", type text}, {"tree_key", type text}, {"scan_key", type text}, {"dbh_input_cm", type number}, {"dbh_input_source", type text}, {"height_m", type number}, {"height_source", type text}, {"coefficient", type number}, {"carbon_d", type number}, {"co2_equivalent_ton", type number}, {"source", type text}, {"formula_version", type text}, {"dataset_kind", type text}}, "en-US")
in Typed

// Query: FactGrowth
let
  Raw = Csv.Document(File.Contents(AnalyticsFolder & "/FactGrowth.csv"), [Delimiter=",", Columns=14, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
  Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars=true]),
  Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
  Typed = Table.TransformColumnTypes(Nulls, {{"tree_key", type text}, {"from_scan_key", type text}, {"to_scan_key", type text}, {"from_observation_key", type text}, {"to_observation_key", type text}, {"from_date", type date}, {"to_date", type date}, {"source", type text}, {"method", type text}, {"days", type number}, {"delta_dbh_cm", type number}, {"annualized_delta_cm", type number}, {"negative_change", type logical}, {"dataset_kind", type text}}, "en-US")
in Typed
