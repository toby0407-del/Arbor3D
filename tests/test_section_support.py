import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location("section_geometry",Path(__file__).resolve().parents[1]/"app/scripts/section_geometry.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SectionSupportTests(unittest.TestCase):
    def test_circle_with_outliers_keeps_original_points_and_recovers_radius(self):
        t=np.linspace(0,4,60)
        p=np.column_stack((2+.2*np.cos(t),3+.2*np.sin(t)))
        p=np.vstack((p,[[2.8,3.5],[1.2,4.]]))
        before=p.copy()
        result=module.fit_section(p)
        self.assertTrue(result['supported'])
        self.assertAlmostEqual(result['candidate_dbh_cm'],40,places=3)
        self.assertEqual(sum(result['inliers']),60)
        np.testing.assert_array_equal(before,p)

    def test_sparse_or_linear_sections_never_get_invented_circle(self):
        for p in ([[0,0],[.2,.3]],np.column_stack((np.linspace(0,1,30),np.linspace(0,1,30)))):
            result=module.fit_section(p)
            self.assertFalse(result['supported'])
            self.assertIsNone(result['candidate_dbh_cm'])

    def test_stable_trunk_surface_can_be_recovered_amid_majority_clutter(self):
        rng=np.random.default_rng(10)
        t=np.linspace(0,4.5,100)
        surface=np.column_stack((.2*np.cos(t),.2*np.sin(t)))
        clutter=rng.uniform(-.8,.8,(110,2))
        result=module.fit_section(np.vstack((surface,clutter)))
        self.assertTrue(result['supported'])
        self.assertAlmostEqual(result['candidate_dbh_cm'],40,delta=1)

    def test_unstructured_scatter_is_not_promoted_to_a_trunk(self):
        cloud=np.random.default_rng(123).uniform(-1,1,(150,2))
        self.assertFalse(module.fit_section(cloud)['supported'])


if __name__ == '__main__':
    unittest.main()
