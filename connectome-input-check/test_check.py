import json
import unittest

from check import InvalidInput, MAX_BODY_ID, MAX_COUNT, canonical_json, validate

MANIFEST = canonical_json({
    "dataset": "Synthetic test", "release": "v1", "source_url": "https://example.com/data",
    "license": "MIT", "license_url": "https://example.com/license", "normalization": "Synthetic directed counts",
})
NODES = b"body_id\n9007199254740992\n9007199254740993\n7\n"
EDGES = b"body_pre,body_post,synapse_count\n9007199254740992,9007199254740993,3\n"


class ValidationTests(unittest.TestCase):
    def test_adjacent_large_ids_remain_distinct(self):
        result = validate(NODES, EDGES, MANIFEST)
        self.assertEqual(result["graph"]["nodes"], ["7", "9007199254740992", "9007199254740993"])
        self.assertEqual(result["graph"]["edges"][0], {"source": "9007199254740992", "target": "9007199254740993", "synapse_count": 3})
        self.assertEqual(result["summary"]["isolated_nodes"], 1)
        # The fixture really exercises the common floating-point collision.
        self.assertEqual(float("9007199254740992"), float("9007199254740993"))

    def test_uint64_maximum_is_accepted(self):
        result = validate(f"body_id\n{MAX_BODY_ID}\n".encode(), b"body_pre,body_post,synapse_count\n", MANIFEST)
        self.assertEqual(result["graph"]["nodes"], [str(MAX_BODY_ID)])

    def test_invalid_ids_rejected(self):
        for value in ("0", "-1", "01", "1.0", "1e3", " 1", "NaN", str(MAX_BODY_ID + 1)):
            with self.subTest(value=value), self.assertRaises(InvalidInput):
                validate(f"body_id\n{value}\n".encode(), EDGES, MANIFEST)

    def test_missing_endpoint_rejected(self):
        with self.assertRaisesRegex(InvalidInput, "endpoint missing"):
            validate(b"body_id\n7\n", EDGES, MANIFEST)

    def test_repeated_nodes_rejected(self):
        with self.assertRaisesRegex(InvalidInput, "duplicate body_id"):
            validate(NODES + b"7\n", EDGES, MANIFEST)

    def test_repeated_pair_not_silently_summed(self):
        with self.assertRaisesRegex(InvalidInput, "repeated directed pair"):
            validate(NODES, EDGES + b"9007199254740992,9007199254740993,4\n", MANIFEST)

    def test_reverse_edges_and_self_edges_preserved(self):
        edges = EDGES + b"9007199254740993,9007199254740992,2\n9007199254740993,9007199254740993,1\n"
        result = validate(NODES, edges, MANIFEST)
        self.assertEqual(result["summary"]["edge_count"], 3)
        self.assertEqual(result["summary"]["total_synapse_count"], "6")

    def test_invalid_counts_rejected(self):
        for value in ("0", "-1", "1.5", "nan", "inf", str(MAX_COUNT + 1)):
            with self.subTest(value=value), self.assertRaises(InvalidInput):
                validate(NODES, f"body_pre,body_post,synapse_count\n7,7,{value}\n".encode(), MANIFEST)

    def test_duplicate_or_wrong_headers_rejected(self):
        for nodes in (b"body_id,body_id\n7,8\n", b"neuron_id\n7\n", b"body_id,extra\n7,x\n"):
            with self.subTest(nodes=nodes), self.assertRaises(InvalidInput):
                validate(nodes, EDGES, MANIFEST)

    def test_malformed_rows_and_encoding_rejected(self):
        for edges in (EDGES + b"7,7\n", EDGES + b"7,7,3,extra\n", EDGES + b'"7,7,3', EDGES + b"\xff"):
            with self.subTest(edges=edges), self.assertRaises(InvalidInput):
                validate(NODES, edges, MANIFEST)

    def test_empty_node_table_rejected_but_empty_edges_allowed(self):
        with self.assertRaises(InvalidInput):
            validate(b"body_id\n", EDGES, MANIFEST)
        self.assertEqual(validate(NODES, b"body_pre,body_post,synapse_count\n", MANIFEST)["summary"]["isolated_nodes"], 3)

    def test_semantic_hash_ignores_row_order_but_input_hash_does_not(self):
        first = validate(NODES, EDGES, MANIFEST)
        reordered = b"body_id\n7\n9007199254740993\n9007199254740992\n"
        second = validate(reordered, EDGES, MANIFEST)
        self.assertEqual(first["graph_sha256"], second["graph_sha256"])
        self.assertNotEqual(first["input_sha256"]["nodes"], second["input_sha256"]["nodes"])

    def test_direction_and_count_affect_semantic_hash(self):
        baseline = validate(NODES, EDGES, MANIFEST)["graph_sha256"]
        for edges in (EDGES.replace(b"0992,9007199254740993", b"0993,9007199254740992"), EDGES.replace(b",3\n", b",4\n")):
            with self.subTest(edges=edges):
                self.assertNotEqual(baseline, validate(NODES, edges, MANIFEST)["graph_sha256"])

    def test_utf8_bom_and_crlf_supported(self):
        baseline = validate(NODES, EDGES, MANIFEST)["graph_sha256"]
        altered = validate(b"\xef\xbb\xbf" + NODES.replace(b"\n", b"\r\n"), EDGES, MANIFEST)
        self.assertEqual(baseline, altered["graph_sha256"])

    def test_bad_manifest_rejected(self):
        for manifest in (b"{}", b"[]", b"not json", MANIFEST.replace(b'"release":"v1"', b'"release":"v1","release":"v2"')):
            with self.subTest(manifest=manifest), self.assertRaises(InvalidInput):
                validate(NODES, EDGES, manifest)
        for source in ("file:///private", "https://user:password@example.com/data", "http://example.com"):
            value = json.loads(MANIFEST)
            value["source_url"] = source
            with self.subTest(source=source), self.assertRaises(InvalidInput):
                validate(NODES, EDGES, canonical_json(value))

    def test_escaped_lone_surrogate_rejected(self):
        for key in json.loads(MANIFEST):
            value = json.loads(MANIFEST)
            value[key] = "\ud800"
            with self.subTest(key=key), self.assertRaisesRegex(InvalidInput, "Unicode scalar"):
                validate(NODES, EDGES, json.dumps(value, ensure_ascii=True).encode("ascii"))


if __name__ == "__main__":
    unittest.main()
