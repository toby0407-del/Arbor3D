import json
from pathlib import Path
import tempfile
import unittest

from park_inventory.best_view import bind_best_views


class BestViewPathsTests(unittest.TestCase):
    def test_custom_output_directory_supplies_registry(self):
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / 'official-output'
            output.mkdir()
            registry = output / 'tree_registry.json'
            registry.write_text(json.dumps({'scan_id': 'fixture', 'trees': []}), encoding='utf-8')
            result = bind_best_views(output_dir=output)
            self.assertEqual(result['source_registry'], str(registry))
            self.assertTrue((output / 'best_views.json').is_file())
            self.assertIn('best_views_bound_at', json.loads(registry.read_text(encoding='utf-8')))

    def test_explicit_registry_overrides_output_location(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry = root / 'input.json'
            registry.write_text(json.dumps({'scan_id': 'fixture', 'trees': []}), encoding='utf-8')
            result = bind_best_views(registry_path=registry, output_dir=root / 'output')
            self.assertEqual(result['source_registry'], str(registry))


if __name__ == '__main__':
    unittest.main()
