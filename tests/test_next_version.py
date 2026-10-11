import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import next_version as nv  # noqa: E402


class NextVersionTest(unittest.TestCase):
    def test_first_release_of_a_minor_starts_at_zero(self):
        self.assertEqual(nv.next_version((1, 1), ["dev-v1.0.4", "prod-v1.0.4"]), "1.1.0")

    def test_bumps_highest_patch(self):
        self.assertEqual(nv.next_version((1, 0), ["dev-v1.0.1", "prod-v1.0.2"]), "1.0.3")

    def test_counts_tags_from_every_environment(self):
        # prod was rejected at 1.0.5, but dev-v1.0.5 exists, so 1.0.5 is taken.
        tags = ["prod-v1.0.4", "staging-v1.0.5", "dev-v1.0.5"]
        self.assertEqual(nv.next_version((1, 0), tags), "1.0.6")

    def test_ignores_unrelated_tags(self):
        tags = ["v9.9.9", "dev-v1.0", "release-candidate", "dev-v1.0.2-rc1"]
        self.assertEqual(nv.next_version((1, 0), tags), "1.0.0")

    def test_no_tags(self):
        self.assertEqual(nv.next_version((2, 3), []), "2.3.0")

    def test_refuses_to_go_backwards(self):
        with self.assertRaises(ValueError):
            nv.next_version((1, 0), ["prod-v1.2.0"])

    def test_parse_base(self):
        self.assertEqual(nv.parse_base("1.0\n"), (1, 0))
        for bad in ["1", "1.0.0", "v1.0", ""]:
            with self.assertRaises(ValueError):
                nv.parse_base(bad)


if __name__ == "__main__":
    unittest.main()
