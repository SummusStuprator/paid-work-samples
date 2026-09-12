"""Validate a small normalized connectome subset; no network or simulation."""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

MAX_BODY_ID = 2**64 - 1
MAX_COUNT = 2**53 - 1


class InvalidInput(ValueError):
    pass


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def positive_integer(value, label, maximum):
    # Never pass identifiers through floats, including apparently integral floats.
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]*", value):
        raise InvalidInput(f"{label}: expected a canonical positive decimal integer")
    if len(value) > len(str(maximum)) or int(value) > maximum:
        raise InvalidInput(f"{label}: value exceeds supported maximum")
    return int(value)


def records(raw, required, label):
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        columns = reader.fieldnames
        if columns is None or len(columns) != len(set(columns)) or set(columns) != set(required):
            raise InvalidInput(f"{label}: headers must be exactly {', '.join(required)} without duplicates")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise InvalidInput(f"{label}: malformed record ending at line {reader.line_num}")
            yield row
    except (UnicodeDecodeError, csv.Error) as exc:
        raise InvalidInput(f"{label}: invalid UTF-8 or CSV") from exc


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput("manifest: duplicate JSON field")
        result[key] = value
    return result


def read_manifest(raw):
    try:
        manifest = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidInput("manifest: invalid UTF-8 or JSON") from exc
    fields = ("dataset", "release", "source_url", "license", "license_url", "normalization")
    if not isinstance(manifest, dict) or set(manifest) != set(fields):
        raise InvalidInput("manifest: requires exactly " + ", ".join(fields))
    if any(not isinstance(manifest[key], str) or not manifest[key].strip() for key in fields):
        raise InvalidInput("manifest: each field must be nonempty text")
    try:
        for key in fields:
            manifest[key].encode("utf-8")
    except UnicodeEncodeError as exc:
        raise InvalidInput("manifest: text must contain valid Unicode scalar values") from exc
    for key in ("source_url", "license_url"):
        try:
            parsed = urlsplit(manifest[key])
            valid = parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
        except ValueError:
            valid = False
        if not valid:
            raise InvalidInput(f"manifest: {key} must be an HTTPS source without embedded credentials")
    return manifest


def validate(nodes_raw, edges_raw, manifest_raw):
    manifest = read_manifest(manifest_raw)
    nodes = set()
    for row in records(nodes_raw, ("body_id",), "nodes"):
        node = row["body_id"]
        positive_integer(node, "body_id", MAX_BODY_ID)
        if node in nodes:
            raise InvalidInput("nodes: duplicate body_id")
        nodes.add(node)
    if not nodes:
        raise InvalidInput("nodes: at least one node is required")

    edges = []
    pairs = set()
    touched = set()
    count = 0
    for row in records(edges_raw, ("body_pre", "body_post", "synapse_count"), "edges"):
        pre, post = row["body_pre"], row["body_post"]
        positive_integer(pre, "body_pre", MAX_BODY_ID)
        positive_integer(post, "body_post", MAX_BODY_ID)
        if pre not in nodes or post not in nodes:
            raise InvalidInput("edges: endpoint missing from node table")
        pair = pre, post
        if pair in pairs:
            raise InvalidInput("edges: repeated directed pair; aggregate under a documented source-specific policy first")
        weight = positive_integer(row["synapse_count"], "synapse_count", MAX_COUNT)
        pairs.add(pair)
        touched.update(pair)
        count += weight
        edges.append({"source": pre, "target": post, "synapse_count": weight})

    graph = {
        "nodes": sorted(nodes, key=int),
        "edges": sorted(edges, key=lambda edge: (int(edge["source"]), int(edge["target"]))),
    }
    return {
        "schema": "summus.connectome-subset.v1",
        "manifest": manifest,
        "provenance_status": "declared, not independently verified by this program",
        "policy": {
            "edge_direction": "presynaptic source to postsynaptic target",
            "duplicate_pairs": "reject",
            "missing_endpoints": "reject",
            "self_edges": "preserve",
            "isolated_nodes": "preserve",
            "counts": "synapse counts, not measured biophysical weights",
        },
        "summary": {"node_count": len(nodes), "edge_count": len(edges), "isolated_nodes": len(nodes - touched), "total_synapse_count": str(count)},
        "input_sha256": {"nodes": digest(nodes_raw), "edges": digest(edges_raw), "manifest": digest(manifest_raw)},
        "graph_sha256": digest(canonical_json(graph)),
        "graph": graph,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nodes", type=Path)
    parser.add_argument("edges", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.nodes.read_bytes(), args.edges.read_bytes(), args.manifest.read_bytes())
    except (InvalidInput, OSError) as exc:
        print(f"Input rejected: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
