# CASF research preprint package

This folder contains the editable manuscript and a rendered reading copy. The paper is a preprint and has not been peer reviewed. No DOI has been assigned.

## Files

- `CASF_Preprint.md`: editable source manuscript.
- `CASF_Preprint.docx`: editable Word copy.
- `CASF_Preprint.pdf`: rendered paper for reading and review.
- `CASF_Research_Figure_1_batching.svg`: editable source for Figure 1.
- `SHA256SUMS.txt`: checksums for these five package files, excluding this checksum list.

Verify package files with `shasum -a 256 -c SHA256SUMS.txt`.

## Software and evidence

The paper is separate from the CASF software and evidence archive. The public repository source used for this manuscript is pinned to commit [`7c388d385242238a40e572ed67e7e5fc9a1ab194`](https://github.com/hamdamme/casf/tree/7c388d385242238a40e572ed67e7e5fc9a1ab194). It contains the CASF implementation, specification, research protocol, public synthetic evidence, and benchmark records. The H1 results record their measurement source commit `7fc4273a941845eac838a5f9fdcba5f2329c9c74`; the H3 results record `1948a982cef52eabbf5cfdb3846d6e9b75ef7413`. Historical benchmark runs retain their own source revisions. The recorded revision for each result must not be replaced with the current revision.

The evidence uses synthetic workloads and keys. The practical PDF demonstration package stays outside the repository and is not part of this deposit. This package contains no private PDF, private fingerprint, key, token, verifier state, or local database.

The H1 report and raw results record a machine specific absolute module path. The originals are preserved unchanged. Publication copies with only that path replaced by `src/casf/__init__.py` are in [`artifacts/h1-writer-rollback-v1/`](artifacts/h1-writer-rollback-v1/); their source and copy hashes and exact replacement are recorded in `SANITIZATION.md`.

Commit references have separate roles: `7fc4273a941845eac838a5f9fdcba5f2329c9c74` is the H1 measurement source commit, `1948a982cef52eabbf5cfdb3846d6e9b75ef7413` is the H3 measurement source commit, and `7c388d385242238a40e572ed67e7e5fc9a1ab194` is the repository revision used to assemble the manuscript and research artifact set. The RQ4 collector's measured snapshot is also recorded separately in its result manifest; it must not be substituted for the manuscript revision.

## Reproduction pointers

Use the repository version above and follow its installation guide. The H1 and H3 experiment documents identify the recorded environment, manifest, exact command, and output fields. A reproduction must write to a new output directory because the saved result paths are protected against overwrite. H1 requires its research harness and the synthetic research adapter described in its report. H3 uses synthetic events and deterministic test keys. Do not treat the historical wide area runs as locally repeatable without the original remote witness service; the runs are preserved as historical evidence.

The included paper archive is not a software release. The software project license is Apache 2.0 as stated in the repository `LICENSE`. That license is not asserted for this manuscript. Zenodo requires a license for each record; the manuscript license still requires the author's decision before deposit.

## AI assistance disclosure for record metadata

Generative AI assistance contributed to the organization and language editing of this manuscript, research question mapping, literature searches and summaries, and Figure 1, which was prepared from previously recorded benchmark values. AI assistance was also used to draft and modify CASF software and experiment tooling, including the H1 rollback harness, tests, and related research documentation. The author made the core research and design decisions, reviewed the AI-assisted code, ran the experiments, and checked the reported results against recorded outputs. The tool was OpenAI Codex; the exact model build and desktop application version were not available in the authoring session. AI did not generate experimental measurements or result values. The author is responsible for the paper and has reviewed its claims, sources, figures, and interpretation.
