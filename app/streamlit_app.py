import streamlit as st
from chat import display_chat
from sidebar import display_sidebar
from api_client import clear_documents

# Set page config
st.set_page_config(
    page_title="Document Q&A",
    page_icon="📚",
)

# Enable dark theme
st.markdown("""<style> [data-testid="stAppViewContainer"] { background-color: #0E1117 } </style>""", unsafe_allow_html=True)

# Clear ChromaDB at the start of each session
if 'db_cleared' not in st.session_state:
    try:
        clear_documents()
        st.session_state.db_cleared = True
        st.session_state.uploaded_files = []
        if "messages" in st.session_state:
            st.session_state.messages = []
    except Exception as e:
        st.error(f"Error clearing previous session data: {str(e)}")

# Display sidebar
display_sidebar()

# Display chat interface
display_chat()