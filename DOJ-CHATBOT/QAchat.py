
import streamlit as st

import google.generativeai as genai

# Load environment variables from .env file
# load_dotenv()

# Configure Google Generative AI with the API key
api_key = "AIzaSyAoMFVEVcctHT3kvAsH_holpTYHaCbEwXg"
if not api_key:
    st.error("GOOGLE_API_KEY is not set. Check your .env file.")
    st.stop()

try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Error configuring Generative AI: {e}")
    st.stop()

# Function to load Gemini Pro model and get responses
try:
    model = genai.GenerativeModel("gemini-pro")
    chat = model.start_chat(history=[])
except Exception as e:
    st.error(f"Error loading Gemini Pro model: {e}")
    st.stop()

def get_gemini_response(question):
    try:
        response = chat.send_message(question, stream=True)
        return response
    except Exception as e:
        st.error(f"Error getting response from Gemini Pro: {e}")
        return []

# Initialize our Streamlit app
st.set_page_config(page_title="Q&A Demo")
st.header("Welcome to ChatBot")

# Initialize session state for chat history if it doesn't exist
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# Create a form to allow submitting the query with "Enter"
with st.form(key='input_form', clear_on_submit=True):
    input = st.text_input("Input: ", key="input")
    submit = st.form_submit_button(label="Ask the question")

if submit and input:
    # Get response from Gemini Pro model
    response = get_gemini_response(input)
    
    # Add user query and response to session state chat history
    st.session_state['chat_history'].append(("You", input))
    st.subheader("The Response is")
    
    # Display the response in chunks
    for chunk in response:
        st.write(chunk.text)
        st.session_state['chat_history'].append(("Bot", chunk.text))

# Display chat history
st.subheader("The Chat History is")
for role, text in st.session_state['chat_history']:
    st.write(f"{role}: {text}")
