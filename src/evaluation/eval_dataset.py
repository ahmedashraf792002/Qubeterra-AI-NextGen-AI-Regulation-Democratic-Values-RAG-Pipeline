"""
Evaluation dataset for the AI Regulations & Democratic Values
knowledge base.

Each entry is one test query with its ground truth: the set of
document_ids a domain-competent reviewer considers relevant to that
query. Relevance is judged at the DOCUMENT level (not chunk level) —
see run_evaluation.py for why.

IMPORTANT — this file is a STARTING TEMPLATE, not a finished ground
truth set:

  Entries q1, q3, q4, and q5 below reference document_ids
  (document_05, document_13, document_14, document_60) that were seen
  in your actual collection/chunking output — their structural labels
  ("Annex III...", "Recital 31...", "Title VII...", "Article 4...")
  came directly from your terminal output, so these are real anchors,
  not invented ones. Everything else (q2, and the exact relevance
  judgments) is a placeholder based on what those topics plausibly
  cover.

  You collected 60 documents; this file only has visibility into the
  handful whose titles/labels appeared in messages so far. Before
  treating this evaluation as valid, YOU must:

    1. Open data/clean/ (or query the DB) and confirm what each
       referenced document actually contains.
    2. Add/correct `relevant_document_ids` for each query based on
       what's ACTUALLY in your corpus — a wrong ground truth produces
       a meaningless precision/recall number, even if the retrieval
       system itself works perfectly.
    3. Add more queries specific to sources you know you collected
       (NIST AI RMF, OECD Principles, UK white paper, etc.) — 5 is the
       assignment's minimum, not a target to stop at.
"""

EVAL_QUERIES = [
    {
        "id": "q1",
        "query": "What activities are classified in Annex III as high-risk AI use cases?",
        "relevant_document_ids": ["document_05"],
        "notes": (
            "Anchored on document_05, whose chunk label was "
            "'Annex III of the AI Act comprises 8 areas in which the use o...' "
            "in your actual chunking output. Verify the full list of areas "
            "and add any other document that also enumerates Annex III "
            "categories (e.g. a news/analysis piece covering the same list)."
        ),
    },
    {
        "id": "q2",
        "query": "What are the transparency obligations for providers of high-risk AI systems?",
        "relevant_document_ids": [],  # TODO: fill in after checking your corpus
        "notes": (
            "PLACEHOLDER — no anchor document confirmed yet. Likely candidates: "
            "any EU AI Act Article 13/52-related source, or an OECD/NIST source "
            "discussing transparency requirements. Search your data/clean/ "
            "files for 'transparency' and fill in the real document_id(s)."
        ),
    },
    {
        "id": "q3",
        "query": "Which AI practices does the AI Act prohibit as posing unacceptable risk?",
        "relevant_document_ids": ["document_13"],
        "notes": (
            "Anchored on document_13, whose chunk label referenced "
            "'Recital 31 of the Act states that it aims to prohibit \"AI sy...' "
            "in your actual chunking output. Confirm the full prohibited-"
            "practices list (e.g. social scoring, manipulative AI, biometric "
            "categorization) and add any other source covering the same ban list."
        ),
    },
    {
        "id": "q4",
        "query": "How does US civil rights law intersect with algorithmic discrimination?",
        "relevant_document_ids": ["document_14"],
        "notes": (
            "Anchored on document_14, whose chunk label referenced "
            "'Title VII of the Civil Rights Act of 1964 prohibits discrimi...' "
            "in your actual chunking output. Verify this document is actually "
            "about AI/algorithmic discrimination specifically, not just "
            "general civil rights law, since Title VII predates AI regulation."
        ),
    },
    {
        "id": "q5",
        "query": "When did the AI Act's provisions on prohibited AI practices enter into force?",
        "relevant_document_ids": ["document_60"],
        "notes": (
            "Anchored on document_60, whose chunk label referenced "
            "'Article 4 of the AI Act entered into application on 2 Februa...' "
            "in your actual chunking output. Confirm the exact date mentioned "
            "and add any other document (news coverage, official timeline "
            "page) that also states this application date."
        ),
    },
]