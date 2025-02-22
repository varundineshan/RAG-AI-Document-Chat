import streamlit as st
from api_client import list_documents, upload_document, delete_document, clear_documents 
# there is already a function to upload the document but using below calls for now
import os

def display_sidebar():
    st.sidebar.header("Settings")

    # Model selector
    model_options = {
        "GPT-3.5 Turbo": "gpt-3.5-turbo",
        "GPT-4": "gpt-4",
    }
    
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "gpt-3.5-turbo"

    selected_model_name = st.sidebar.selectbox(
        "Choose GPT Model",
        options=list(model_options.keys()),
        index=0
    )
    st.session_state.selected_model = model_options[selected_model_name]

    st.sidebar.divider()
    
    # Document Management section
    st.sidebar.header("Document Management")
    
    # Initialize uploaded files list in session state
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []

    # Display list of documents first
    st.sidebar.subheader("Available Documents")
    
    # Display uploaded documents
    if st.session_state.uploaded_files:
        for filename in st.session_state.uploaded_files:
            st.sidebar.success(f"📄 {filename}")
    else:
        st.sidebar.info("No documents uploaded yet")

    # File uploader below the document list
    uploaded_files = st.sidebar.file_uploader(
        "Upload documents", 
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True,
        help="Upload PDF, Word, or text documents to add to the knowledge base"
    )
    
    if uploaded_files:
        if st.sidebar.button("Process Documents"):
            with st.spinner("Processing documents..."):
                try:
                    for uploaded_file in uploaded_files:
                        if uploaded_file.name not in st.session_state.uploaded_files:
                            response = upload_document(uploaded_file)
                            if response and response.get("status") == "success":
                                if uploaded_file.name not in st.session_state.uploaded_files:
                                    st.session_state.uploaded_files.append(uploaded_file.name)
                            else:
                                st.sidebar.error(f"❌ Failed to process {uploaded_file.name}")
                    
                   
                    st.sidebar.success("✅ Documents processed successfully!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"❌ Error: {str(e)}")

    # Add a clear documents button if documents are uploaded
    if st.session_state.uploaded_files:
        if st.sidebar.button("Clear All Documents"):
            try:
                response = clear_documents()
                if response and response.get("status") == "success":
                    st.session_state.uploaded_files = []
                    # Clear chat history
                    if "messages" in st.session_state:
                        st.session_state.messages = []
                    st.rerun()
                else:
                    st.sidebar.error("❌ Failed to clear documents")
            except Exception as e:
                st.sidebar.error(f"❌ Error clearing documents: {str(e)}")

    st.sidebar.divider()