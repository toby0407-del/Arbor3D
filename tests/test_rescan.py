import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from measurement_quality.rescan import build_rescan_plan, save_task, write_overlay
from scripts.postprocess_from_inbox import publish_report


def points(bins):
    t = np.radians(np.array(list(bins))*5 + 2.5)
    return np.column_stack((.2*np.cos(t), .2*np.sin(t)))


QUALITY = dict(decision="review", identifiable=True, reasons=["missing_calibration"])


class RescanTests(unittest.TestCase):
    def test_wraparound_gap_is_one_region_and_no_covered_bins_added(self):
        plan = build_rescan_plan(points(range(2, 70)), (0, 0), .2, QUALITY)
        self.assertEqual(plan["minimum_scope_deg"], 20)
        self.assertEqual(plan["sectors"], [dict(start_deg=350, end_deg=10, span_deg=20, view_local_deg=0)])
        self.assertFalse(plan["precision_guaranteed"])
        self.assertEqual(plan["safety_status"], "unverified")

    def test_disconnected_missing_regions_keep_separate_and_priority(self):
        missing = {4, 5, 6, 30, 31}
        plan = build_rescan_plan(points(set(range(72))-missing), (0, 0), .2, QUALITY)
        self.assertEqual([s["span_deg"] for s in plan["sectors"]], [15, 10])
        self.assertEqual(plan["minimum_scope_deg"], 25)
        self.assertEqual(plan["next_view_local_deg"], 27.5)

    def test_uncertain_geometry_or_non_breast_height_has_no_direction(self):
        for q, strict in (({**QUALITY, "identifiable": False}, True), (QUALITY, False)):
            plan = build_rescan_plan(points(range(30)), (0, 0), .2, q, strict)
            self.assertEqual(plan["status"], "manual_review")
            self.assertEqual(plan["sectors"], [])
            self.assertIsNone(plan["next_view_local_deg"])

    def test_full_ring_does_not_invent_gap_to_fix_calibration(self):
        plan = build_rescan_plan(points(range(72)), (0, 0), .2, QUALITY)
        self.assertTrue(plan["required"])
        self.assertEqual(plan["status"], "manual_review")
        self.assertFalse(plan["sectors"])

    def test_successful_remeasurement_closes_task_without_duplicate_or_cross_scan_collision(self):
        plan = build_rescan_plan(points(range(30)), (0, 0), .2, QUALITY)
        closed = build_rescan_plan(points(range(30)), (0, 0), .2, {**QUALITY, "decision": "accepted", "reasons":[],
            "schema_version":"arbor3d-quality-1", "method":"circle", "model_id":"test-only",
            "probability":.97,"target_probability":.95,"tolerance_cm":1})
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder)/"tasks.sqlite"
            save_task(file, "scan-a", "Tree_001", plan, "first")
            save_task(file, "scan-b", "Tree_001", plan, "second")
            save_task(file, "scan-a", "Tree_001", closed, "third")
            with closing(sqlite3.connect(file)) as db:
                rows = db.execute("SELECT scan_id, required, status FROM rescan_tasks ORDER BY scan_id").fetchall()
            self.assertEqual(rows, [("scan-a", 0, "complete"), ("scan-b", 1, "pending_safety_check")])

    def test_overlay_requires_registration_and_embeds_original(self):
        plan = build_rescan_plan(points(range(70)), (0, 0), .2, QUALITY)
        with tempfile.TemporaryDirectory() as folder:
            png = Path(folder)/"section.png"
            png.write_bytes(b"original-image-bytes")
            self.assertIsNone(write_overlay(png, plan))
            png.with_suffix(".plot.json").write_text(json.dumps(dict(size_px=[500,500],axes_px=[50,50,400,400],xlim=[-.3,.3],ylim=[-.3,.3])))
            result = write_overlay(png, plan)
            tree = ET.parse(result)
            ns = {"s":"http://www.w3.org/2000/svg"}
            self.assertTrue(tree.find("s:image", ns).attrib["href"].startswith("data:image/png;base64,"))
            self.assertEqual(len(tree.findall("s:g/s:path", ns)), 1)
            self.assertTrue(plan["overlay_available"])

    def test_publishing_copies_matching_overlay_and_keeps_task_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            png = root/"section.png"
            png.write_bytes(b"unchanged-source")
            svg = root/"section_rescan.svg"
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            plan = build_rescan_plan(points(range(30)), (0,0), .2, QUALITY)
            report_file = root/"report.json"
            report_file.write_text(json.dumps({"trees":[{"Tree_ID":"Tree_003","Cross_Section_Image":str(png),"Rescan_Overlay_Image":str(svg),"rescan_plan":plan}]}))
            report = publish_report(report_file,root,root/"repo",root,"scan-b","")
            tree = report["trees"][0]
            self.assertEqual(tree["Rescan_Overlay_Image"], "dbh/Tree_003_section_rescan.svg")
            self.assertEqual(tree["rescan_plan"], plan)
            self.assertEqual((root/"repo/app/public/scans/scan-b"/tree["Rescan_Overlay_Image"]).read_bytes(),svg.read_bytes())


if __name__ == "__main__":
    unittest.main()
