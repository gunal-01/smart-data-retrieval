import requests
from langchain.text_splitter import CharacterTextSplitter
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 1. Fetch JSON data from an endpoint
def fetch_json(endpoint_url):
    """Fetch JSON data from a given API endpoint."""
    response = requests.get(endpoint_url)
    response.raise_for_status()
    return response.json()

# 2. Convert JSON data to a flattened text format
def parse_json_to_text(json_data):
    """Convert nested JSON into a plain text representation."""
    def flatten(obj, parent_key='', sep='.'):
        """Flatten nested JSON recursively."""
        items = []
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    items.extend(flatten(item, f"{new_key}[{i}]", sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    flattened = flatten(json_data)
    return "\n".join(f"{k}: {v}" for k, v in flattened.items())

# 3. Text splitting
def split_text(text):
    """Split text into smaller chunks."""
    text_splitter = CharacterTextSplitter(chunk_size=7500, chunk_overlap=100)
    return text_splitter.split_text(text)

# 4. Main pipeline
def main():
    # Endpoint URL
    endpoint_url = "https://sdr-rag-60035688705.development.catalystserverless.in/server/sdr_rag_function/all"  # Replace with the actual endpoint

    # Fetch and parse JSON data
    print("Fetching JSON data...")
    json_data = fetch_json(endpoint_url)
    text_data = parse_json_to_text(json_data)
    print("JSON data converted to text.")

    # Split text into chunks
    print("Splitting text into chunks...")
    text_chunks = split_text(text_data)

    # Convert chunks to embeddings and store in Chroma
    print("Generating embeddings...")
    embedding_model = OllamaEmbeddings(model="nomic-embed-text")
    vectorstore = Chroma.from_texts(
        texts=text_chunks,
        collection_name="rag-chroma",
        embedding=embedding_model,
    )
    retriever = vectorstore.as_retriever()

    # RAG: Question answering after embeddings
    print("\nRAG")
    model_local = ChatOllama(model="mistral")  # model
    after_rag_template = """Answer the question based only on the following context:
{context}
Question: {question}
"""
    after_rag_prompt = ChatPromptTemplate.from_template(after_rag_template)
    after_rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | after_rag_prompt
        | model_local
        | StrOutputParser()
    )
    print(after_rag_chain.invoke("Based on the dataset, give me the customer count?"))

if __name__ == "__main__":
    main()

