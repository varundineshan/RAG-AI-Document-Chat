from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from langchain_utils import get_rag_chain, process_document, save_uploaded_file, clear_vectorstore
import config
from db_utils import (
    insert_application_logs,
    get_chat_history,
    get_all_documents,
    insert_document_record,
    delete_document_record
)
from chroma_utils import index_document_to_chroma, delete_doc_from_chroma
import os
import uuid
import logging
import uvicorn
import shutil
import json
from datetime import datetime

# Basic logging setup
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    filename=f'logs/app_{datetime.now().strftime("%Y%m%d")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logger.info(json.dumps({
        'event': 'startup',
        'timestamp': datetime.now().isoformat(),
        'message': 'FastAPI application starting up'
    }))

# Define data models
class QueryInput(BaseModel):
    question: str
    session_id: Optional[str] = None
    model: str = "GPT_3_5_TURBO"

class QueryResponse(BaseModel):
    answer: str
    session_id: str
    model: str

class DocumentInfo(BaseModel):
    file_id: str

class DeleteFileRequest(BaseModel):
    file_id: str

class UploadResponse(BaseModel):
    message: str
    status: str

@app.post("/chat")
async def chat(query_input: QueryInput):
    session_id = query_input.session_id or str(uuid.uuid4())
    try:
        logger.info(f"Received chat request", extra={
            'session_id': session_id,
            'question': query_input.question,
            'answer': 'N/A',
            'file_name': 'N/A'
        })
        
        chain = get_rag_chain(model_name=query_input.model)
        result = chain({
            "question": query_input.question,
            "chat_history": []
        })
        
        answer = result['answer'].strip()
        source_docs = result.get('source_documents', [])
        
        # Filter sources to only include those referenced in the answer
        answer_lower = answer.lower()
        relevant_sources = {}
        
        for doc in source_docs:
            content = doc.page_content.strip()
            content_lower = content.lower()
            
            # Check if significant parts of the content appear in the answer
            key_phrases = content_lower.split('.')
            for phrase in key_phrases:
                if phrase and len(phrase.strip()) > 20 and any(part.strip() in answer_lower for part in phrase.split(',')):
                    relevant_sources[content] = doc.metadata
                    break
        
        # If no sources were found to be relevant, use the first source
        if not relevant_sources and source_docs:
            doc = source_docs[0]
            relevant_sources[doc.page_content.strip()] = doc.metadata
        
        logger.info(f"Chat response generated", extra={
            'session_id': session_id,
            'question': query_input.question,
            'answer': answer,
            'file_name': str([doc.get('source', 'N/A') for doc in [m for _, m in relevant_sources.items()]])
        })
        
        return {
            "answer": answer,
            "sources": list(relevant_sources.items()),
            "session_id": session_id,
            "model": query_input.model
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in chat: {error_msg}", extra={
            'session_id': session_id,
            'question': query_input.question,
            'answer': error_msg,
            'file_name': 'N/A'
        })
        return {
            "answer": error_msg,
            "sources": [],
            "session_id": session_id,
            "model": query_input.model
        }

@app.post("/upload-doc")
async def upload_document(file: UploadFile = File(...)):
    temp_file_path = None
    try:
        # Log with file information
        logger.info(
            "Starting upload process",
            extra={
                'file_name': file.filename,
                'session_id': 'upload',
                'question': 'N/A',
                'answer': 'N/A'
            }
        )
        
        # Create temp directory if it doesn't exist
        temp_dir = "temp_uploads"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        # Save file to temp directory , there is already a function to save the file to the temp directory but using this one for now
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the document
        success = process_document(temp_file_path)
        
        if success:
            logger.info(
                "Document processed successfully",
                extra={
                    'file_name': file.filename,
                    'session_id': 'upload',
                    'question': 'N/A',
                    'answer': 'N/A'
                }
            )
            return {
                "message": f"File {file.filename} uploaded and processed successfully",
                "status": "success"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to process document"
            )
            
    except Exception as e:
        logger.error(
            f"Error during upload: {str(e)}",
            extra={
                'file_name': file.filename,
                'session_id': 'upload',
                'question': 'N/A',
                'answer': 'N/A'
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error processing upload: {str(e)}"
        )
        
    finally:
        # Cleanup temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning(
                    f"Failed to cleanup temp file: {str(e)}",
                    extra={
                        'file_name': file.filename,
                        'session_id': 'upload',
                        'question': 'N/A',
                        'answer': 'N/A'
                    }
                )

@app.get("/list-docs")
async def list_documents():
    try:
        return []  # Return empty list for now
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete-doc")
async def delete_document(file_id: str):
    try:
        return {"message": f"File {file_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear-documents")
async def clear_documents():
    try:
        logger.info("Clearing all documents", extra={
            'session_id': 'clear',
            'question': 'N/A',
            'answer': 'N/A',
            'file_name': 'all'
        })
        
        success = clear_vectorstore()
        
        if success:
            # Clear any temporary files
            temp_dir = "temp_uploads"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            logger.info("Documents cleared successfully", extra={
                'session_id': 'clear',
                'question': 'N/A',
                'answer': 'success',
                'file_name': 'all'
            })
            return {"message": "Documents cleared successfully", "status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear documents")
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error clearing documents: {error_msg}", extra={
            'session_id': 'clear',
            'question': 'N/A',
            'answer': error_msg,
            'file_name': 'all'
        })
        raise HTTPException(status_code=500, detail=f"Failed to clear documents: {error_msg}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)