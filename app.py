import streamlit as st
import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

st.title("DeepSeek AI Assistant")
st.markdown("🚀 A streaming AI assistant powered by DeepSeek")

# History management functions
def load_conversations():
    try:
        with open("chat_history.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_conversations(conversations):
    with open("chat_history.json", "w") as f:
        json.dump(conversations, f, indent=2)

# Initialize session state
if "current_messages" not in st.session_state:
    st.session_state.current_messages = []

if "past_conversations" not in st.session_state:
    st.session_state.past_conversations = load_conversations()

if "selected_conversation_id" not in st.session_state:
    st.session_state.selected_conversation_id = None

# Sidebar with history
with st.sidebar:
    st.header("History")
    
    # New Chat button
    if st.button("New Chat"):
        # Save current conversation if not empty
        if len(st.session_state.current_messages) > 0:
            new_conv = {
                "id": len(st.session_state.past_conversations),
                "timestamp": datetime.now().isoformat(),
                "messages": st.session_state.current_messages.copy()
            }
            st.session_state.past_conversations.append(new_conv)
            save_conversations(st.session_state.past_conversations)
        # Reset state
        st.session_state.current_messages = []
        st.session_state.selected_conversation_id = None
        st.rerun()
    
    # Display past conversations
    st.subheader("Previous Chats")
    for conv in st.session_state.past_conversations:
        btn_label = datetime.fromisoformat(conv["timestamp"]).strftime("%Y-%m-%d %H:%M")
        if st.button(btn_label, key=f"conv_{conv['id']}"):
            st.session_state.selected_conversation_id = conv["id"]
            st.session_state.current_messages = conv["messages"].copy()
            st.rerun()
    
    # Clear history button
    if st.button("Clear All History"):
        st.session_state.past_conversations = []
        save_conversations([])
        st.rerun()

# Main chat interface
def generate_response(messages):
    """Generator function to stream responses from DeepSeek API"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        yield "❌ API key missing. Please set the environment variable `DEEPSEEK_API_KEY`."
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "stream": True,
        "max_tokens": 1000,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True
        )
        
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
            except json.JSONDecodeError:
                error_msg = response.text
            yield f"❌ API Error ({response.status_code}): {error_msg}"
            return

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data:"):
                    json_data = decoded_line[5:].strip()
                    if json_data == "[DONE]":
                        return
                    
                    try:
                        chunk = json.loads(json_data)
                        content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                        yield content
                    except json.JSONDecodeError:
                        yield "⏳ Decoding error..."
                    except Exception as e:
                        yield f"⏳ Processing error: {str(e)}"
    except Exception as e:
        yield f"❌ Connection Error: {str(e)}"

# Display messages
for message in st.session_state.current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle chat input
if st.session_state.selected_conversation_id is None:
    if prompt := st.chat_input("What would you like to ask?"):
        # Add user message
        st.session_state.current_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display assistant response
        assistant_response = ""
        with st.chat_message("assistant"):
            response_container = st.empty()
            payload_messages = [{"role": msg["role"], "content": msg["content"]} 
                               for msg in st.session_state.current_messages]
            
            try:
                for chunk in generate_response(payload_messages):
                    assistant_response += chunk
                    response_container.markdown(assistant_response + "▌")
                response_container.markdown(assistant_response)
            except Exception as e:
                st.error(f"Error during streaming: {str(e)}")
        
        # Add assistant response
        st.session_state.current_messages.append({"role": "assistant", "content": assistant_response})
else:
    st.chat_input("Select 'New Chat' to start a new conversation", disabled=True)

# Save current conversation when it contains messages and isn't in history
if len(st.session_state.current_messages) > 0 and st.session_state.selected_conversation_id is None:
    current_conv_exists = any(conv["id"] == "current" for conv in st.session_state.past_conversations)
    if not current_conv_exists:
        new_conv = {
            "id": "current",
            "timestamp": datetime.now().isoformat(),
            "messages": st.session_state.current_messages.copy()
        }
        st.session_state.past_conversations.append(new_conv)
        save_conversations(st.session_state.past_conversations)