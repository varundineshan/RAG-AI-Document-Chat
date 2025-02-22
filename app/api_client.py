import requests
from typing import Optional
import streamlit as st
import json

API_BASE_URL = "http://localhost:8000"  # Adjust if your FastAPI server is on a different port

def handle_api_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend server. Please ensure the FastAPI server is running on localhost:8000")
            return None
        except json.JSONDecodeError:
            st.error("Received invalid response from server")
            return None
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None
    return wrapper

@handle_api_error
def chat(question: str, session_id: Optional[str] = None, model: str = "gpt-3.5-turbo"):
    response = requests.post(
        f"{API_BASE_URL}/chat",
        json={
            "question": question,
            "session_id": session_id,
            "model": model
        }
    )
    response.raise_for_status()  # Raise an exception for bad status codes
    return response.json()

@handle_api_error
def list_documents():
    response = requests.get(f"{API_BASE_URL}/list-docs")
    response.raise_for_status()
    return response.json() or []

@handle_api_error
def upload_document(file):
    files = {"file": (file.name, file, "application/octet-stream")}
    response = requests.post(f"{API_BASE_URL}/upload-doc", files=files)
    if response.status_code != 200:
        raise Exception(f"Upload failed: {response.text}")
    return response.json()

@handle_api_error
def delete_document(file_id: str):
    response = requests.post(
        f"{API_BASE_URL}/delete-doc",
        json={"file_id": file_id}
    )
    response.raise_for_status()
    return response.json()

@handle_api_error
def clear_documents():
    """Clear all documents from the knowledge base"""
    response = requests.post(f"{API_BASE_URL}/clear-documents")
    response.raise_for_status()
    return response.json() 