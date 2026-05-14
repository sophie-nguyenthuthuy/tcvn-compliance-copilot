# Standards corpus

This package holds the **metadata** for every TCVN/QCVN standard the copilot
knows about. The actual standard documents (PDF, DOCX, scanned, etc.) are
**not** stored in this repository — they are copyrighted by the Ministry of
Construction (Bộ Xây dựng) and must be supplied by the operator at deploy time.

## Layout

```
packages/standards-corpus/
├── README.md            ← you are here
├── manifests/           ← one YAML per standard; checked into git
│   ├── QCVN_06_2022.yml
│   ├── QCVN_10_2014.yml
│   └── TCVN_2737_2023.yml
├── samples/             ← short, public-domain or fabricated samples for tests
│   └── tcvn_sample.txt
├── raw/                 ← operator-supplied source files (gitignored)
└── processed/           ← intermediate text extracts (gitignored)
```

## Contributing a new standard

1. Obtain the latest official PDF or DOCX of the standard from
   `https://moc.gov.vn` or `vbpl.vn`.
2. Drop the file under `packages/standards-corpus/raw/<CODE>/<file>.pdf`.
3. Create or update `manifests/<CODE>.yml` describing it.
4. Run `make corpus-validate` to lint the manifest.
5. Run `make corpus-ingest` (or `--standard <CODE>`) to (re-)embed the clauses.

The pipeline is idempotent — re-running with unchanged source skips embedding.

## Manifest schema

```yaml
code: QCVN_06_2022          # unique key (UPPER_SNAKE_CASE)
title_vi: "..."             # Vietnamese title
title_en: "..."             # English title (optional)
issuer: "Bộ Xây dựng"
version: "2022"
issued_at: 2022-04-06
effective_at: 2023-01-16
source_file: "raw/QCVN_06_2022/QCVN-06-2022-BXD.pdf"
description: "..."
tags:
  - fire_safety
  - egress
```

## Why not check in the PDFs?

- Copyright. TCVN/QCVN texts are property of the Ministry of Construction;
  redistribution requires licensing.
- Size. A single standard can be 20-100 MB; keeping git lean matters.
- Versioning. The PDFs are mirrored on `vbpl.vn` and `moc.gov.vn`; pinning by
  `source_hash` in the database gives us reproducibility without storing bytes.
