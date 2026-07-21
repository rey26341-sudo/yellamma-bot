"""
preview_voices.py

Quick one-off script — NOT part of the app. Generates a short sample
clip for each candidate voice so you can listen and pick one before
setting DEFAULT_VOICE_NAME in app/voice/tts.py.

Run from your repo root (venv activated, ADC already set up):
    python3 preview_voices.py

Then play the resulting .wav files however's easiest on your setup,
e.g.:
    # if you have a player available in WSL:
    aplay leda.wav
    # or copy them to Windows and double-click:
    cp *.wav /mnt/c/Users/YOUR_WINDOWS_USERNAME/Desktop/
"""

from google.cloud import texttospeech

SAMPLE_TEXT = (
    "Welcome to our clinic. I'm here to help you book an appointment, "
    "no rush at all. May I have your name, please?"
)

VOICES_TO_TRY = [
    "en-IN-Chirp3-HD-Leda",
    "en-IN-Chirp3-HD-Kore",
    "en-IN-Chirp3-HD-Aoede",
    "en-IN-Chirp3-HD-Achernar",
]

client = texttospeech.TextToSpeechClient()
synthesis_input = texttospeech.SynthesisInput(text=SAMPLE_TEXT)

for voice_name in VOICES_TO_TRY:
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-IN",
        name=voice_name,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=24000,  # higher quality for listening than the 8kHz used on real calls
        speaking_rate=0.95,
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    filename = f"{voice_name.split('-')[-1].lower()}.wav"
    with open(filename, "wb") as f:
        f.write(response.audio_content)
    print(f"Wrote {filename}")

print("\nDone. Listen to each file and pick your favorite.")
