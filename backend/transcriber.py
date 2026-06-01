import os
from groq import Groq

def transcribe_audio(audio_path):
    try:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        with open(audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), file.read()),
                model="whisper-large-v3",
                response_format="json",
            )
        return transcription.text
    except Exception as e:
        print("Transcription Error:", e)
        return ""