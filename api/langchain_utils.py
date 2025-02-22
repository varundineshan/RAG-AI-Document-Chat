from langchain_community.chat_models import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredFileLoader
)
from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import logging
import tempfile
import shutil
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "document_collection"

def ensure_directory(dir_path: str):
    """Ensure a directory exists, create if it doesn't"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        logger.info(f"Created directory: {dir_path}")

def load_document(file_path: str):
    """Load a document using the appropriate loader"""
    logger.info(f"Loading document: {file_path}")
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            loader = PyPDFLoader(file_path)
        elif file_extension == '.docx':
            loader = Docx2txtLoader(file_path)
        elif file_extension == '.txt':
            loader = TextLoader(file_path)
        else:
            loader = UnstructuredFileLoader(file_path)
        
        documents = loader.load()
        logger.info(f"Successfully loaded {len(documents)} document segments")
        return documents
    
    except Exception as e:
        logger.error(f"Error loading document: {str(e)}", exc_info=True)
        raise

def process_document(file_path: str) -> bool:
    """Process a document and add it to the vector store"""
    try:
        logger.info(f"Processing document: {file_path}")
        
        # Load the document
        documents = load_document(file_path)
        if not documents:
            logger.error("No content loaded from document")
            return False

        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        texts = text_splitter.split_documents(documents)
        logger.info(f"Split document into {len(texts)} chunks")
        
        if not texts:
            logger.error("No text chunks created")
            return False
            
        # Initialize embeddings
        embeddings = OpenAIEmbeddings()
        
        # Get or create vectorstore
        if os.path.exists(CHROMA_DB_DIR):
            # Add to existing vectorstore
            vectorstore = Chroma(
                persist_directory=CHROMA_DB_DIR,
                embedding_function=embeddings,
                collection_name=COLLECTION_NAME
            )
        else:
            # Create new vectorstore
            vectorstore = Chroma.from_documents(
                documents=texts,
                embedding=embeddings,
                persist_directory=CHROMA_DB_DIR,
                collection_name=COLLECTION_NAME
            )
        
        # Add documents to existing store
        if os.path.exists(CHROMA_DB_DIR):
            vectorstore.add_documents(texts)
        
        # Persist the vectorstore
        vectorstore.persist()
        logger.info("Successfully persisted vector store")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in process_document: {str(e)}", exc_info=True)
        return False

def get_vectorstore() -> Optional[Chroma]:
    """Get the vector store if it exists"""
    try:
        ensure_directory(CHROMA_DB_DIR)
        embeddings = OpenAIEmbeddings()
        
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME
        )
        
        return vectorstore
    except Exception as e:
        logger.error(f"Error getting vector store: {str(e)}", exc_info=True)
        return None

def check_vectorstore_empty() -> bool:
    """Check if the vector store has any documents"""
    try:
        vectorstore = get_vectorstore()
        if not vectorstore:
            return True
            
        collection = vectorstore._collection
        count = collection.count()
        logger.info(f"Vector store contains {count} documents")
        return count == 0
        
    except Exception as e:
        logger.error(f"Error checking vector store: {str(e)}", exc_info=True)
        return True

def get_rag_chain(model_name: str = "gpt-3.5-turbo"):
    """Get RAG chain for question answering"""
    try:
        # Check if ChromaDB directory exists and has content
        if not os.path.exists(CHROMA_DB_DIR) or not os.listdir(CHROMA_DB_DIR):
            raise ValueError("No documents found in the knowledge base. Please upload a document first.")

        # Initialize embeddings
        embeddings = OpenAIEmbeddings()
        
        # Load the vector store
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME
        )
        
        # Verify the collection has documents
        if vectorstore._collection.count() == 0:
            raise ValueError("No documents found in the knowledge base. Please upload a document first.")

        # Create retriever
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )

        # Create LLM
        llm = ChatOpenAI(model_name=model_name, temperature=0)

        # Create chain
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            return_source_documents=True
        )

        return chain
    except Exception as e:
        logger.error(f"Error in get_rag_chain: {str(e)}")
        raise ValueError("No documents found in the knowledge base. Please upload a document first.")

def save_uploaded_file(uploaded_file) -> str:
    """Save an uploaded file and return its path"""
    try:
        suffix = os.path.splitext(uploaded_file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in uploaded_file.file:
                tmp.write(chunk)
            tmp.flush()
            logger.info(f"Saved uploaded file to temporary location: {tmp.name}")
            return tmp.name
    except Exception as e:
        logger.error(f"Error saving uploaded file: {str(e)}", exc_info=True)
        raise

def clear_vectorstore() -> bool:
    """Clear the vector store and its contents"""
    try:
        logger.info(f"Clearing vector store at: {CHROMA_DB_DIR}")
        
        # Get a new client instance
        try:
            import chromadb
            client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
            
            # Delete the collection if it exists
            try:
                client.delete_collection(COLLECTION_NAME)
                logger.info("Deleted existing collection")
            except Exception as e:
                logger.info(f"No collection to delete: {e}")
                
            # Reset the client
            client.reset()
            
        except Exception as e:
            logger.warning(f"Error while cleaning up ChromaDB: {e}")
        
        # Remove the directory if it exists
        if os.path.exists(CHROMA_DB_DIR):
            try:
                shutil.rmtree(CHROMA_DB_DIR)
                logger.info("Removed ChromaDB directory")
            except Exception as e:
                logger.warning(f"Error removing ChromaDB directory: {e}")
                
        # Recreate empty directory
        os.makedirs(CHROMA_DB_DIR, exist_ok=True)
        logger.info("Created fresh ChromaDB directory")
        
        # Delete any temporary files
        temp_dir = "temp_uploads"
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info("Removed temporary uploads directory")
            except Exception as e:
                logger.warning(f"Error removing temp directory: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in clear_vectorstore: {str(e)}", exc_info=True)
        return False