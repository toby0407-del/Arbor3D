import unittest
import numpy as np

from measurement_quality import assess, section_features, suggest_views
from measurement_quality.core import FEATURES
from measurement_quality.__main__ import calibrate, wilson_lower


CONTEXT = dict(scale_verified=True, pose_verified=True, breast_height_verified=True,
               view_direction_verified=True, left_boundary_visible=True, right_boundary_visible=True,
               near_circular_verified=True, cropped=False, sensor_id="test", protocol_id="fixture")


def ring(degrees=360, n=200):
    t = np.linspace(0, np.radians(degrees), n, endpoint=False)
    return np.column_stack((.2*np.cos(t), .2*np.sin(t)))


class QualityTests(unittest.TestCase):
    def test_repeated_points_do_not_inflate_support(self):
        p = ring()
        a = section_features(p, (0,0), .2)
        b = section_features(np.repeat(p, 10, axis=0), (0,0), .2)
        self.assertEqual(a, b)
        self.assertGreater(a["occupied_fraction"], .95)

    def test_short_arc_low_residual_still_ill_conditioned(self):
        f = section_features(ring(.01), (0,0), .2)
        q = assess(f, "circle", CONTEXT)
        self.assertEqual(q["decision"], "review")
        self.assertFalse(q["identifiable"])

    def test_without_calibration_even_full_ring_is_not_accepted(self):
        q = assess(section_features(ring(), (0,0), .2), "circle", CONTEXT)
        self.assertTrue(q["identifiable"])
        self.assertIsNone(q["probability"])
        self.assertIn("missing_calibration", q["reasons"])

    def test_caliper_needs_both_tangent_boundaries(self):
        context = {**CONTEXT, "left_boundary_visible": False}
        q = assess(section_features(ring(120), (0,0), .2), "caliper", context)
        self.assertIn("left_boundary_visible_required", q["reasons"])
        self.assertFalse(q["identifiable"])

    def test_no_unsafe_or_unknown_view_can_win(self):
        safe = dict(azimuth_deg=90,new_coverage_deg=30,time_s=10,safe=True,reachable=True)
        result = suggest_views([safe, {**safe,"azimuth_deg":180,"new_coverage_deg":300,"safe":False}, {**safe,"safe":None}])
        self.assertEqual(len(result["candidates"]), 1)
        self.assertIsNone(result["candidates"][0]["precision_gain"])
        self.assertEqual(suggest_views([])["decision"], "manual_review")

    def test_model_scope_and_domain_fail_closed(self):
        f = dict(zip(FEATURES,[100,1,5,.001,2,80]))
        m = {"schema_version":"arbor3d-quality-1", "scope":{"sensor_id":"test","protocol_id":"fixture"},
             "feature_names":list(FEATURES),"target_probability":.95,"tolerance_cm":1,"model_id":"fixture-only",
             "policy_validation":{"passed":True},
             "methods":{"circle":{"validation":{"passed":True},"bounds":[[v-1,v+1] for v in f.values()],
               "mean":list(f.values()),"scale":[1]*6,"weights":[10]+[0]*6,"sigmoid":[1,0]}}}
        self.assertEqual(assess(f,"circle",CONTEXT,m)["decision"], "accepted")
        self.assertEqual(assess({**f,"effective_points":500},"circle",CONTEXT,m)["decision"], "review")
        self.assertIn("calibration_scope_mismatch",assess(f,"circle",{**CONTEXT,"sensor_id":"other"},m)["reasons"])
        m["methods"]["circle"]["validation"]["passed"] = False
        self.assertIsNone(assess(f,"circle",CONTEXT,m)["probability"])

    def bundle(self):
        rows=[]
        for split in ("train","calibration","test"):
            for i in range(12):
                rows.append(dict(source="observed",persistent_tree_id=f"{split}-{i}",split=split,
                    scan_id=split,tree_id=str(i),method="circle",scan_date="2026-01-01",manual_date="2026-01-01",strict_13m=True,
                    candidate_dbh_cm=20 if i%2 else 24,manual_dbh_cm=20,context=CONTEXT.copy(),
                    features=dict(zip(FEATURES,[100+i, .8, 50, .001+i*.001, 2+i, 80]))))
        return {"scope":{"sensor_id":"test","protocol_id":"fixture"},"rows":rows}

    def test_training_rejects_leakage_simulation_and_repeated_test_trees(self):
        for mutation in ("source","leakage","repeat"):
            b = self.bundle()
            if mutation == "source":b["rows"][0]["source"]="simulated"
            elif mutation == "leakage":b["rows"][-1]["persistent_tree_id"]=b["rows"][0]["persistent_tree_id"]
            else:b["rows"][-1]["persistent_tree_id"]=b["rows"][-2]["persistent_tree_id"]
            with self.assertRaises(ValueError):calibrate(b)

    def test_small_test_set_cannot_claim_95_percent_reliability(self):
        model = calibrate(self.bundle())
        self.assertFalse(model["methods"]["circle"]["validation"]["passed"])
        self.assertLess(wilson_lower(12,12),.95)


if __name__ == "__main__":
    unittest.main()
