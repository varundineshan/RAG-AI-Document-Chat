import streamlit as st
from api_client import chat

def display_chat_interface():
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Use the selected model from session state
                model = st.session_state.get("selected_model", "gpt-3.5-turbo")
                response = chat(prompt, st.session_state.session_id, model)
                
                if response is None:
                    error_message = "Sorry, I encountered an error. Please try again."
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
                else:
                    st.markdown(response.get('answer', 'No response received'))
                    st.session_state.session_id = response.get('session_id')
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response.get('answer', 'No response received')
                    })