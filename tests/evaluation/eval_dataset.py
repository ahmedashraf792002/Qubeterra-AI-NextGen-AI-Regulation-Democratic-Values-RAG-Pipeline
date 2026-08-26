"""
Evaluation dataset: Q&A pairs generated from clean documents.

Relevance judged at DOCUMENT level — each query lists which document_ids
are considered relevant sources for that question.
"""

EVAL_QUERIES = [
    {
        "id": "Q1",
        "query": "What are the transparency obligations for high-risk AI systems?",
        "relevant_document_ids": ["document_01", "document_05", "document_37"],
    },
    {
        "id": "Q2",
        "query": "What does the EU AI Act say about prohibited AI practices?",
        "relevant_document_ids": ["document_01", "document_29"],
    },
    {
        "id": "Q3",
        "query": "How does the NIST AI Risk Management Framework work?",
        "relevant_document_ids": ["document_07", "document_08", "document_10"],
    },
    {
        "id": "Q4",
        "query": "What are the OECD AI Principles?",
        "relevant_document_ids": ["document_12"],
    },
    {
        "id": "Q5",
        "query": "What is the timeline for the EU AI Act implementation?",
        "relevant_document_ids": ["document_06"],
    },
    {
        "id": "Q6",
        "query": "What are the risk categories defined in the AI Act?",
        "relevant_document_ids": ["document_01", "document_05"],
    },
    {
        "id": "Q7",
        "query": "What obligations do deployers of high-risk AI systems have?",
        "relevant_document_ids": ["document_05", "document_36"],
    },
    {
        "id": "Q8",
        "query": "How does UNESCO approach AI ethics?",
        "relevant_document_ids": ["document_13"],
    },
    {
        "id": "Q9",
        "query": "What is the role of the European AI Office?",
        "relevant_document_ids": ["document_02", "document_03"],
    },
    {
        "id": "Q10",
        "query": "What standards support the EU AI Act?",
        "relevant_document_ids": ["document_04"],
    },
    {
        "id": "Q11",
        "query": "What are the obligations for general-purpose AI models?",
        "relevant_document_ids": ["document_36"],
    },
    {
        "id": "Q12",
        "query": "How is the AI Act governed and enforced?",
        "relevant_document_ids": ["document_55", "document_58"],
    },
    {
        "id": "Q13",
        "query": "What is the AI Pact and how does it work?",
        "relevant_document_ids": ["document_60"],
    },
    {
        "id": "Q14",
        "query": "What is the EU AI Act impact assessment about?",
        "relevant_document_ids": ["document_38"],
    },
    {
        "id": "Q15",
        "query": "What are the EU guidelines on AI system definition?",
        "relevant_document_ids": ["document_28"],
    },
]
