import unittest

from prospective_validation_ledger.canonical import (
    canonical_json_bytes,
    sha256_json,
)


class CanonicalJsonTest(unittest.TestCase):
    def test_sorted_compact_utf8_bytes_match_golden_vector(self):
        value = {"b": "雪", "a": 1}
        self.assertEqual(
            canonical_json_bytes(value),
            b'{"a":1,"b":"\xe9\x9b\xaa"}',
        )
        self.assertEqual(
            sha256_json(value),
            "f317713ac99270129844375745820bbf1f628cff9a4b11d3e67e16129ff6e0d3",
        )

    def test_non_finite_number_is_rejected(self):
        with self.assertRaises(ValueError):
            canonical_json_bytes({"value": float("nan")})


if __name__ == "__main__":
    unittest.main()
