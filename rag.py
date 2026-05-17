import os
from typing import Dict, List

from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter


class FinancialRAG:
    def __init__(self, persist_directory: str = "db/chroma", collection_name: str = "financial_docs"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = self._load_or_create_store()

    def _load_or_create_store(self):
        if os.path.exists(self.persist_directory) and os.listdir(self.persist_directory):
            return Chroma(
                persist_directory=self.persist_directory,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
            )
        return None

    def ingest_documents(self, documents: List[Dict[str, str]]) -> str:
        texts = [doc["text"] for doc in documents]
        metadatas = [{"source": doc.get("source", "personal_finance")} for doc in documents]
        self.vectorstore = Chroma.from_texts(
            texts,
            self.embeddings,
            metadatas=metadatas,
            persist_directory=self.persist_directory,
            collection_name=self.collection_name,
        )
        return f"Ingested {len(texts)} financial documents into the knowledge base."

    def query(self, query: str, k: int = 3) -> str:
        if not self.vectorstore:
            return "The financial knowledge base is not initialized yet."

        results = self.vectorstore.similarity_search(query, k=k)
        if not results:
            return "No relevant financial documents were found."

        return "\n\n".join(
            [f"Source: {getattr(doc, 'metadata', {}).get('source', 'unknown')}\n{doc.page_content}" for doc in results]
        )

    @staticmethod
    def default_documents() -> List[Dict[str, str]]:
        return [
            {
                "source": "Personal Goal",
                "text": "User wants to save $5,000 for an emergency fund by the end of the year and reduce discretionary spending by 20%.",
            },
            {
                "source": "Bank Statement",
                "text": "2026-06-01: Grocery $82.40, 2026-06-03: Coffee $6.75, 2026-06-05: Gas $45.12, 2026-06-07: Subscription $12.99.",
            },
            {
                "source": "Bank Statement",
                "text": "2026-06-10: Gym membership $29.99, 2026-06-12: Utilities $120.50, 2026-06-14: Dining out $56.30.",
            },
            {
                "source": "Financial Advice",
                "text": "A smart budget includes categories for essentials, savings, debt repayment, and discretionary spending. Track irregular expenses and keep at least three months of income in reserves.",
            },
        ]
