import os
import chromadb
from langchain.tools import tool

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DB_DIR = os.path.join(BASE_DIR, "knowledge_base", "chroma_db")

def get_retrieve_guidelines_tool(collection_name: str):
    """Factory function to create a retrieve_guidelines tool for a specific collection."""
    
    @tool("retrieve_guidelines")
    def retrieve_guidelines(query: str) -> str:
        """
        Queries the designated guidelines collection and returns the most relevant chunks.
        Always provide a specific search query.
        """
        client = chromadb.PersistentClient(path=os.path.join(CHROMA_DB_DIR, collection_name))
        collection_db_name = f"{collection_name}_kb"
        collection = client.get_collection(name=collection_db_name)
        
        results = collection.query(
            query_texts=[query],
            n_results=3
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant guidelines found."
            
        combined_results = []
        for i, doc in enumerate(results['documents'][0]):
            source = results['metadatas'][0][i].get('source', 'Unknown Source') if results['metadatas'] else 'Unknown Source'
            combined_results.append(f"Source: {source}\nContent: {doc}")
            
        return "\n\n---\n\n".join(combined_results)
        
    return retrieve_guidelines
