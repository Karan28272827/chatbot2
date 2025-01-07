import streamlit as st
import requests
import json
from docx import Document
from PyPDF2 import PdfReader
from elevenlabs import ElevenLabs
from elevenlabs import VoiceSettings
import pygame
import tempfile
import os
import base64  

# Initialize ElevenLabs client
elevenlabs_client = ElevenLabs(api_key="ae38aba75e228787e91ac4991fc771f8")  # Replace with your ElevenLabs API key

# Function to extract text from PDF
def extract_text_from_pdf(uploaded_pdf):
    pdf_reader = PdfReader(uploaded_pdf)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Function to extract text from Word file
def extract_text_from_word(file):
    doc = Document(file)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text

# Function to query the Chatbot API
def ask_question(question, context, model_name="azure/gpt-4o"):
    api_url = "https://llm.kindo.ai/v1/chat/completions"
    headers = {
        "api-key": "09e75bff-6192-436d-936e-2d0f9230a3a6-a896f6311e363485",  # Replace with your API key
        "content-type": "application/json"
    }
    
    messages = [
        {"role": "system", "content": "You are Navin Kale, the co-founder of Swayam Talks. Answer in English and in short paragraphs, not more than 100 words. Use natural human speech, you can also pause in between sentences for a more human-like response."},
        {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
    ]
    
    data = {
        "model": model_name,
        "messages": messages
    }
    
    response = requests.post(api_url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json().get('choices', [{}])[0].get('message', {}).get('content', "").strip()
    else:
        st.error(f"API request failed with status code {response.status_code}")
        return None

# Function to play audio using pygame
def play_audio_stream(audio_stream):
    pygame.mixer.init()
    
    # Save audio stream to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        for chunk in audio_stream:
            temp_audio.write(chunk)
        temp_audio_name = temp_audio.name

    # Load and play the audio file
    pygame.mixer.music.load(temp_audio_name)
    pygame.mixer.music.play()
    
    # Wait until the audio is finished
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

# Function to convert text to speech
def text_to_speech(text, voice_id="voice_id"):
    try:
        audio_stream = elevenlabs_client.text_to_speech.convert_as_stream(
            voice_id=voice_id,
            text=text, 
            model_id="eleven_multilingual_v2",  # Added missing comma here
            voice_settings=VoiceSettings(stability=0.5,
                                         similarity_boost=0.75,
                                         style=0.0)
        )
        play_audio_stream(audio_stream)
    except Exception as e:
        st.error(f"Text-to-speech conversion failed: {e}")

# Function to capture speech and convert it to text using the API Key directly
def speech_to_text(audio_file_path, api_key):
    # Define the API URL
    url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
 
    # Read and encode the audio file
    with open(audio_file_path, "rb") as audio_file:
        audio_content = base64.b64encode(audio_file.read()).decode("utf-8")
 
    # Create the request payload
    payload = {
        "config": {
            "encoding": "LINEAR16",  # Change based on your audio file format
            "sampleRateHertz": 16000,  # Replace with your audio's sample rate
            "languageCode": "en-US"
        },
        "audio": {
            "content": audio_content
        }
    }
 
    # Send the request to the API
    response = requests.post(url, json=payload)
 
    # Check the response
    if response.status_code == 200:
        result = response.json()
        if "results" in result:
            transcript = result["results"][0]["alternatives"][0]["transcript"]
            return f"Transcript: {transcript}"
        else:
            return "No speech recognized in the audio."
    else:
        return f"Error: {response.status_code}, {response.text}"

# Streamlit app
def main():
    st.title("Swayam Talks Chatbot")

    # Initialize session state for Q&A history
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []

    # Upload PDF file
    uploaded_pdf = st.file_uploader("Upload a PDF file", type=["pdf"])
    if uploaded_pdf:
        try:
            # Extract text from the uploaded PDF
            context = extract_text_from_pdf(uploaded_pdf)
        except Exception as e:
            st.error(f"Error extracting text from PDF: {e}")
            return

        # Input for questions (either type or speak)
        question_type = st.radio("How do you want to ask the question?", ("Type", "Speak"))

        if question_type == "Type":
            question = st.text_input("Ask a question:")
        elif question_type == "Speak":
            # Capture speech using a temporary audio file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
                # Assume you captured the speech here (you can integrate a recognizer or use any method)
                # For example, save the audio content to `temp_audio_file.name`
                # temp_audio_file.write(audio_content)
                
                # Pass the path to the speech-to-text function
                question = speech_to_text(temp_audio_file.name, "AIzaSyDCm8ZTQMO_vs7RDMrkneE8EBs0AHV1w5o")  # Replace with your API key

        if question:
            # Get the answer from the API
            answer = ask_question(question, context, model_name="azure/gpt-4o")
            if answer:
                # Add question and answer to session state
                st.session_state.qa_history.append((question, answer))
                
                # Convert answer to speech
                text_to_speech(answer, voice_id="okq89CVMFdUItYbOQspc")  # Replace with your ElevenLabs voice ID

    # Display Q&A history
    if st.session_state.qa_history:
        st.write("### Question-Answer History:")
        for i, (q, a) in enumerate(st.session_state.qa_history, 1):
            with st.expander(f"Q{i}: {q}"):
                st.write(a)

if __name__ == "__main__":
    main()
