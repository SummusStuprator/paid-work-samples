# Connectome input boundary — synthetic demonstration

This small Python tool checks a **normalized, directed subset graph before it enters a simulation**. It is an AI-authored implementation sample, not a brain simulator, scientific result, or completed MaleCNS importer. All included neuron identifiers and connections are invented.

Run with Python 3.10+; no dependencies, accounts, network access or writes:

```sh
python -m unittest -v
python check.py nodes.csv edges.csv manifest.json
```

The included fixture produces four nodes, three directed edges, two isolated nodes and a total synapse count of six. Two adjacent identifiers above JavaScript's exact-integer range remain different strings. That is a robustness fixture: **it is not evidence of a defect in MaleCNS data**. The published MaleCNS segmentation currently leaves the upper 32 bits of its uint64 IDs unused.

## What is checked

| Input | Contract |
|---|---|
| Node CSV | Exactly `body_id`; unique positive uint64 IDs written as canonical decimal strings. No floats, exponent notation, whitespace or leading zeros. |
| Edge CSV | Exactly `body_pre,body_post,synapse_count`; each endpoint exists in the node table; counts are positive integers no greater than 2^53−1. |
| Pair identity | Presynaptic source → postsynaptic target. Reverse pairs and self-edges remain distinct; repeated directed pairs are rejected. Isolated nodes are retained. |
| Manifest | Dataset/release, source and licence URLs, licence label, and a description of normalization. This records a declaration; it does **not** verify the licence or download the source. |

`graph_sha256` hashes canonical nodes and directed counts, independent of CSV row order. `input_sha256` separately hashes the original file bytes, including the manifest. A changed count or reversed edge changes the graph hash. A hash identifies bytes or normalized content; it does not prove authenticity, biological correctness or a time of commitment.

Sixteen tests cover the identifier collision, uint64 bounds, malformed CSV/JSON and Unicode, duplicate headers/nodes/pairs, dangling endpoints, invalid counts, preserved reverse/self-edges and isolated nodes, row-order invariance, changed direction/count and UTF-8 BOM/CRLF input. Rejected inputs exit with status 2 and produce no graph JSON.

## Why raw data needs a separate adapter

The [MaleCNS download page](https://male-cns.janelia.org/download/) lists the v1.0 full connection graph as a 1.1 GB Feather file, alongside separate synapse-partner records and annotations. This demo does not read Feather and does not download those files. It loads inputs into memory and is intended for small, already normalized subsets.

The [upstream flat-graph exporter](https://github.com/janelia-flyem/flyem-snapshot/blob/e6357d20044f648c3fd516d0daa4e63c8b11ee7c/flyem_snapshot/outputs/flat.py#L238) counts `body_pre,body_post` pairs into a `weight` column. Raw synaptic partner rows can legitimately repeat a body pair; the aggregated graph should have one record per directed pair. A pre-synaptic site can also have several post-synaptic partners. Treating either raw repetition as a duplicate to delete would lose connectivity.

An actual adapter must therefore pin the release and confidence threshold, inspect its real schema, distinguish synaptic records from aggregated pairs, retain uncurated segments when annotations are absent, and document the exact subset and transformations. It must also preserve attribution and modification notices under the dataset's published CC-BY licence. The [project release history](https://male-cns.janelia.org/) distinguishes the June 8 v1.0 release from the September 3 paper publication.

Synapse counts are connectivity measurements, **not measured biophysical weights**. This sample supplies no neurotransmitter signs, dynamics, sensory encoding, action decoding or evidence of behaviour. Its MIT licence covers only this code and synthetic fixture, not any future imported dataset.

## Proposed paid adaptation

A proposed **USD 150** milestone is an adapter and validation report for one agreed, licence-checked MaleCNS subset: source/version manifest, explicit normalization policy, an executable import command, failure fixtures and one revision. Real input acquisition, output format, size and acceptance checks must be agreed before that work starts. This public sample is free evidence of the approach; it is not an invoice or a claim that anyone has funded the milestone.

Contact: **suedtluv1@gmail.com** · Summus Code
