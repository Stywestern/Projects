# ==========================================
# 1. IMPORTS & SETUP
# ==========================================

# Third-Party Libraries
import os
import torch
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Load environment variables
load_dotenv()

# Define flexible paths relative to this script
CURRENT_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(CURRENT_DIR, "../vector_db")

# ==========================================
# 2. HELPERS
# ==========================================
def format_docs(docs):
    """
    Helper function to turn a list of Document objects into a single string.
    """
    return "\n\n".join(doc.page_content for doc in docs)

# ==========================================
# 3. MAIN PROCESS
# ==========================================

def query_rag(question: str):
    # ---------------------------------------------------------
    # Step 1: Hardware Check
    # ---------------------------------------------------------
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device.upper()}")

    # ---------------------------------------------------------
    # Step 2. Database & Embeddings
    # ---------------------------------------------------------
    embedding_function = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': device}
    )
    
    vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embedding_function)
    retriever = vector_db.as_retriever(search_kwargs={"k": 3})

    # ---------------------------------------------------------
    # Step 3. Load LLM
    # ---------------------------------------------------------
    llm = ChatOllama(model="mistral", temperature=0)

    # ---------------------------------------------------------
    # Step 4. Prompt Template
    # ---------------------------------------------------------
    template = """Answer the question based only on the following context:
    {context}

    Question: {question}
    """
    prompt = ChatPromptTemplate.from_template(template)

    # ---------------------------------------------------------
    # Step 5. The Chain
    # ---------------------------------------------------------
    # The pipe (|) passes data from left to right.
    # 1. Retrieves docs and formats them -> "context"
    # 2. Passes the user's question -> "question"
    # 3. Sends both to Prompt -> LLM -> String Parser
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # ---------------------------------------------------------
    # Step 6. Execution
    # ---------------------------------------------------------
    print(f"\nQuestion: {question}")
    print("Thinking...")
    
    result = rag_chain.invoke(question)
    
    print(f"\nAnswer: {result}")
    return result

if __name__ == "__main__":
    # Try
    query_rag("What is the policy on sick leave?")