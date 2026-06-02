from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings

PERSIST_DIR = "./chroma_db_v2"

embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-2",
    google_api_key=os.environ.get("GEMINI_API_KEY")
)


def _get_vectordb():
    return Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embedding_model,
    )


def clear_video_chunks(video_id: str):
    """Delete all existing chunks for a video_id before re-ingesting."""
    try:
        vectordb = _get_vectordb()
        collection = vectordb._collection
        existing = collection.get(where={"video_id": video_id})
        ids = existing.get("ids", [])
        if ids:
            collection.delete(ids=ids)
            print(f"Cleared {len(ids)} existing chunks for video_id={video_id}")
    except Exception as e:
        print(f"Warning: Could not clear chunks for {video_id}: {e}")


def store_transcript(transcript: str, video_id: str) -> int:
    # Clear old chunks for this video_id first
    clear_video_chunks(video_id)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    chunks = splitter.split_text(transcript)
    chunks = [c.strip() for c in chunks if c.strip()]

    print(f"Chunks for {video_id}: {len(chunks)}")

    if not chunks:
        raise Exception("No documents created — transcript may be empty")

    docs = [
        Document(
            page_content=chunk,
            metadata={"video_id": video_id, "chunk_id": i},
        )
        for i, chunk in enumerate(chunks)
    ]

    vectordb = _get_vectordb()
    vectordb.add_documents(docs)

    return len(chunks)


def search_transcript(query: str, video_id: str, k: int = 4):
    """Search chunks for a single video."""
    vectordb = _get_vectordb()
    return vectordb.similarity_search(
        query,
        k=k,
        filter={"video_id": video_id},
    )


def search_both_transcripts(query: str, k_each: int = 3):
    """Search chunks across both Video A and Video B."""
    vectordb = _get_vectordb()
    results_a = vectordb.similarity_search(
        query, k=k_each, filter={"video_id": "A"}
    )
    results_b = vectordb.similarity_search(
        query, k=k_each, filter={"video_id": "B"}
    )
    return results_a + results_b


def get_retriever(video_id: str):
    """Return a LangChain retriever filtered to one video."""
    vectordb = _get_vectordb()
    return vectordb.as_retriever(
        search_kwargs={"k": 4, "filter": {"video_id": video_id}}
    )


def get_combined_retriever():
    """Return a retriever that searches both videos (no filter)."""
    vectordb = _get_vectordb()
    return vectordb.as_retriever(search_kwargs={"k": 6})