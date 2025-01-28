import streamlit as st
import requests
import os
import json

# Load environment variables - modified for Streamlit Cloud compatibility
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Skip if python-dotenv isn't installed

st.title("DeepSeek AI Assistant")
st.markdown("🚀 A streaming AI assistant powered by DeepSeek")

def generate_response(messages):
    # Get API key from environment variables (Streamlit secrets)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        yield "❌ API key missing. Please set DEEPSEEK_API_KEY in environment variables."
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

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What would you like to ask?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    assistant_response = ""
    with st.chat_message("assistant"):
        response_container = st.empty()

        payload_messages = [{"role": msg["role"], "content": msg["content"]} 
                           for msg in st.session_state.messages]

        try:
            for chunk in generate_response(payload_messages):
                assistant_response += chunk
                response_container.markdown(assistant_response + "▌")
            response_container.markdown(assistant_response)  # Remove cursor
        except Exception as e:
            st.error(f"Error during streaming: {str(e)}")

    st.session_state.messages.append({"role": "assistant", "content": assistant_response})