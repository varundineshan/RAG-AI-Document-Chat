import streamlit as st
from api_client import chat

def display_chat():
    st.title("Document Q&A")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("View Sources"):
                    for i, (content, metadata) in enumerate(message["sources"], 1):
                        st.markdown(f"**Source {i}:**")
                        if metadata.get('source'):
                            st.markdown(f"*From: {metadata['source']}*")
                        st.markdown(content[:200] + "...")
                        st.divider()

    # Chat input
    if prompt := st.chat_input("Ask a question about your documents"):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = chat(
                    question=prompt,
                    model=st.session_state.selected_model
                )
                
                if response:
                    st.markdown(response["answer"])
                    if response.get("sources"):
                        with st.expander("View Sources"):
                            for i, (content, metadata) in enumerate(response["sources"], 1):
                                st.markdown(f"**Source {i}:**")
                                if metadata.get('source'):
                                    st.markdown(f"*From: {metadata['source']}*")
                                st.markdown(content[:200] + "...")
                                st.divider()
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response["answer"],
                        "sources": response.get("sources", [])
                    })
                else:
                    st.error("Failed to get response from the assistant") 