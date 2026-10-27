export type DbhMethod = "circle" | "caliper" | string;

export type MeasurementQuality = {
  schema_version: string;
  method: string;
  decision: "accepted" | "review";
  identifiable: boolean;
  probability: number | null;
  target_probability: number;
  tolerance_cm: number | null;
  model_id: string | null;
  reasons: string[];
  features: Record<string, number | null>;
  context?: Record<string, unknown>;
};

export type QuarterlyObservation = {
  dataset_kind: "simulated";
  persistent_tree_id: string;
  quarter: string;
  date: string;
  scenario: string;
  simulated_manual_dbh_cm: number;
  simulated_ai_dbh_cm: number;
  simulated_height_m: number;
  simulated_latitude: number;
  simulated_longitude: number;
};

export type TreeRecord = {
  Tree_ID: string;
  persistent_tree_id?: string;
  candidate_dbh_cm?: number | null;
  execution?: { platform: string; stage: string; id?: string; completed_at?: string; input_sha256?: string; point_count?: number } | null;
  num_slice_points?: number | null;
  measurement_quality?: MeasurementQuality | null;
  quality_candidates?: (MeasurementQuality & { candidate_dbh_cm: number })[] | null;
  dataset_kind?: "observed" | "simulated";
  quarterly_observations?: QuarterlyObservation[];
  DBH_cm: number | null;
  previous_DBH_cm?: number | null;
  DBH_method: DbhMethod;
  DBH_note: string;
  arc_coverage_deg: number | null;
  dbh_is_strict_breast_height: boolean;
  Height_m?: number | null;
  GPS_Location: [number, number] | null;
  Local_XYZ_m: [number, number, number];
  Best_Photo: string | null;
  PointCloud_Preview?: string | null;
  Mask_Path: string | null;
  Cross_Section_Image: string | null;
  "3D_Model_Path": string | null;
  Single_Tree_Ply: string | null;
  YOLO_confidence: number | null;
  num_detections: number | null;
};

export type ParkInventoryReport = {
  created_at: string;
  scan_id: string;
  dataset_kind?: "observed" | "simulated";
  simulation_notice?: string;
  simulation_media_source?: string;
  gps_available: boolean;
  num_trees: number;
  trees: TreeRecord[];
};

export type TrafficLight = "green" | "yellow" | "red";
