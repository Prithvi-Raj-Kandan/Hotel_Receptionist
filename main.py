from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import io
import time
import base64
import re
from pydub import AudioSegment
from deepgram import Deepgram
from elevenlabs import ElevenLabs
from datetime import datetime

# Import agent function from lcmdb
from lcmdb import execute_react_with_memory

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
DOWNLOAD_DIR = "downloads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def log_process(message, start_time=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    if start_time:
        elapsed = time.time() - start_time
        print(f"[{timestamp}] {message} (elapsed: {elapsed:.2f}s)")
    else:
        print(f"[{timestamp}] {message}")

# Initialize Deepgram
log_process("Initializing Deepgram client...")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY environment variable not set")
deepgram = Deepgram(DEEPGRAM_API_KEY)
log_process("✓ Deepgram client initialized")

# Initialize ElevenLabs
log_process("Initializing ElevenLabs client...")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY environment variable not set")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
log_process("✓ ElevenLabs client initialized")

log_process("🚀 VoiceBot backend ready!")

import re

def parse_agent_response(response: str) -> str:
    """
    Converts raw agent response with markdown tables and formatting
    into human-readable text for TTS and frontend display.
    """
    if not response:
        return ""

    # 1. Remove bold/italic markdown (**text**, *text*)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", response)
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)

    # 2. Split into lines for table detection
    lines = cleaned.splitlines()

    table_data = []
    non_table_lines = []

    for line in lines:
        if "|" in line and not line.strip().startswith("|---"):  # skip divider rows
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) >= 2:
                table_data.append(cells)
        else:
            non_table_lines.append(line)

    # 3. Convert table rows → sentences
    sentences = []
    if table_data:
        headers = table_data[0]  # first row is header
        for row in table_data[1:]:
            entry = ", ".join(f"{headers[i]} is {row[i]}" for i in range(min(len(headers), len(row))))
            sentences.append(f"{entry}.")

    # 4. Combine
    response_no_table = " ".join(non_table_lines).strip()
    final_response = response_no_table + " " + " ".join(sentences)

    # 5. Normalize spaces
    return " ".join(final_response.split()).strip()



@app.post("/voicebot")
async def voicebot(file: UploadFile = File(...)):
    overall_start = time.time()
    log_process("🤖 VoiceBot workflow started", overall_start)

    # 1. STT
    audio_bytes = await file.read()
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
    audio = audio.set_frame_rate(16000).set_channels(1)
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)
    try:
        response = await deepgram.transcription.prerecorded({
            "buffer": wav_io.read(),
            "mimetype": "audio/wav"
        }, {
            "smart_format": True,
            "model": "nova-2",
            "language": "en-US"
        })
        text = response["results"]["channels"][0]["alternatives"][0]["transcript"]
        log_process(f"📝 Transcribed text: '{text}'", overall_start)
    except Exception as e:
        log_process(f"❌ Deepgram STT failed: {e}", overall_start)
        return {"error": f"STT failed: {str(e)}"}

    # 2. Agent
    try:
        agent_response = execute_react_with_memory("session_1", text)
        log_process(f"🤖 Agent response: '{agent_response}'", overall_start)
    except Exception as e:
        log_process(f"❌ Agent failed: {e}", overall_start)
        return {"error": f"Agent failed: {str(e)}"}
    clean_response = parse_agent_response(agent_response)
    log_process(f"🪄 Parsed response: '{clean_response}'")

    # 3. TTS
    try:
        audio_stream = elevenlabs_client.text_to_speech.convert(
            text=clean_response,
            voice_id="ulTHPKT60YxEfyrVgZFh",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            )
        audio_bytes = b"".join(audio_stream)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        output_filename = f"output_{abs(hash(clean_response)) % (10 ** 8)}.mp3"
        output_path = os.path.join(DOWNLOAD_DIR, output_filename)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        log_process(f"✓ Output audio saved: {output_path}", overall_start)
    except Exception as e:
        log_process(f"❌ ElevenLabs TTS failed: {e}", overall_start)
        return {"error": f"TTS failed: {str(e)}"}

    return {
        "transcript": text,
        "agent_response": clean_response,
        "audio_base64": audio_base64,
        "output_audio_path": output_path
    }
