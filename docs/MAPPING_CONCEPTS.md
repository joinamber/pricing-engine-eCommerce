# Mapping Concepts

## Runtime mapping

Runtime means mapping a newly observed competitor listing to one SKU in the catalog, rather than answering a pairwise question against a preselected target SKU.

## Recall

Recall measures whether the correct candidate was retrieved. Recall@K asks whether the correct SKU appears in the first K candidates.

```text
Recall@1 -> correct SKU ranked first
Recall@3 -> correct SKU in top three
Recall@5 -> correct SKU in top five
```

Candidate retrieval should optimize recall; identity resolution should optimize precision and safe abstention.

## Family + critical attributes

Normalize each SKU into family and structured identity attributes, then filter contradictions before bounded model reasoning.

Examples of critical attributes:
- MacBook: family, chip/generation, screen size, memory, storage.
- iPad: family, generation/chip, screen size, storage, connectivity.
- Watch: family, generation, case size, GPS/Cellular.
- AirPods: family, generation, Pro/standard, ANC.
- Power adapter: wattage and port configuration.

## Shadow mode

A new mapping system runs on real observations alongside the authoritative path but cannot affect production. Its decisions are logged and compared with human ground truth.

Progression: offline evaluation -> shadow -> assisted human approval -> limited automation -> broader automation.
