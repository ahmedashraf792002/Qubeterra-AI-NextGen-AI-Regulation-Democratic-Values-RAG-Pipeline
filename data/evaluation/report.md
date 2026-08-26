# Retrieval Evaluation Report

Top-K: 5
Queries evaluated: 5 (4 with ground truth defined)

## Summary metrics

- Mean Precision@5: 0.400
- Mean Recall@5: 1.000
- Mean Reciprocal Rank: 0.708

## Per-query results

### q1: What activities are classified in Annex III as high-risk AI use cases?

- Relevant documents (ground truth): ['document_05']
- Precision@5: 1.00
- Recall@5: 1.00
- Reciprocal Rank: 1.00

| Rank | Chunk | Document | Similarity | Relevant? |
|---|---|---|---|---|
| 1 | document_05_chunk034 | document_05 | 0.8449 | ✓ |
| 2 | document_05_chunk033 | document_05 | 0.8348 | ✓ |
| 3 | document_05_chunk032 | document_05 | 0.8221 | ✓ |
| 4 | document_05_chunk020 | document_05 | 0.7873 | ✓ |
| 5 | document_05_chunk013 | document_05 | 0.7582 | ✓ |

### q2: What are the transparency obligations for providers of high-risk AI systems?

- Relevant documents (ground truth): (none defined)
- Precision@5: 0.00
- Recall@5: N/A
- Reciprocal Rank: 0.00

| Rank | Chunk | Document | Similarity | Relevant? |
|---|---|---|---|---|
| 1 | document_60_chunk011 | document_60 | 0.8591 |  |
| 2 | document_05_chunk039 | document_05 | 0.8556 |  |
| 3 | document_01_chunk019 | document_01 | 0.8549 |  |
| 4 | document_05_chunk040 | document_05 | 0.8532 |  |
| 5 | document_05_chunk076 | document_05 | 0.8383 |  |

### q3: Which AI practices does the AI Act prohibit as posing unacceptable risk?

- Relevant documents (ground truth): ['document_13']
- Precision@5: 0.20
- Recall@5: 1.00
- Reciprocal Rank: 0.33

| Rank | Chunk | Document | Similarity | Relevant? |
|---|---|---|---|---|
| 1 | document_01_chunk006 | document_01 | 0.8657 |  |
| 2 | document_14_chunk005 | document_14 | 0.7957 |  |
| 3 | document_13_chunk005 | document_13 | 0.7957 | ✓ |
| 4 | document_01_chunk010 | document_01 | 0.7910 |  |
| 5 | document_27_chunk002 | document_27 | 0.7875 |  |

### q4: How does US civil rights law intersect with algorithmic discrimination?

- Relevant documents (ground truth): ['document_14']
- Precision@5: 0.20
- Recall@5: 1.00
- Reciprocal Rank: 1.00

| Rank | Chunk | Document | Similarity | Relevant? |
|---|---|---|---|---|
| 1 | document_14_chunk039 | document_14 | 0.7253 | ✓ |
| 2 | document_13_chunk039 | document_13 | 0.7253 |  |
| 3 | document_05_chunk048 | document_05 | 0.7242 |  |
| 4 | document_15_chunk037 | document_15 | 0.7108 |  |
| 5 | document_55_chunk006 | document_55 | 0.6867 |  |

### q5: When did the AI Act's provisions on prohibited AI practices enter into force?

- Relevant documents (ground truth): ['document_60']
- Precision@5: 0.20
- Recall@5: 1.00
- Reciprocal Rank: 0.50

| Rank | Chunk | Document | Similarity | Relevant? |
|---|---|---|---|---|
| 1 | document_01_chunk033 | document_01 | 0.8309 |  |
| 2 | document_60_chunk000 | document_60 | 0.8058 | ✓ |
| 3 | document_13_chunk003 | document_13 | 0.7981 |  |
| 4 | document_14_chunk003 | document_14 | 0.7981 |  |
| 5 | document_05_chunk082 | document_05 | 0.7808 |  |

## Interpretation

_(Fill in after reviewing the results above)_

## Known weaknesses

- Relevance judged at document level, not chunk level.
- No re-ranking or hybrid keyword search; pure vector similarity.
- Ground truth must be expanded before results are final.
