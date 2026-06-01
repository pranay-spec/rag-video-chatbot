import whisper

model = whisper.load_model("base")

result = model.transcribe(
    "downloads/audio.webm"
)

print(result["text"])