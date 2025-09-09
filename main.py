from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import io
import time
import base64
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

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    overall_start = time.time()
    log_process("🎤 STT Request: Starting speech-to-text conversion", overall_start)
    audio_bytes = await file.read()
    input_path = os.path.join(UPLOAD_DIR, file.filename or "input.webm")
    with open(input_path, "wb") as f:
        f.write(audio_bytes)
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
        return {"text": text, "input_audio_path": input_path}
    except Exception as e:
        log_process(f"❌ Deepgram STT failed: {e}", overall_start)
        return {"error": f"STT failed: {str(e)}"}

class TTSRequest(BaseModel):
    text: str

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    overall_start = time.time()
    log_process("🔊 TTS Request: Starting text-to-speech conversion", overall_start)
    try:
        audio_stream = elevenlabs_client.text_to_speech.convert(
            voice_id="ulTHPKT60YxEfyrVgZFh",
            text=request.text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_stream)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        output_filename = f"output_{abs(hash(request.text)) % (10 ** 8)}.mp3"
        output_path = os.path.join(DOWNLOAD_DIR, output_filename)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        log_process(f"✓ Output audio saved: {output_path}", overall_start)
        return {"audio_base64": audio_base64, "output_audio_path": output_path}
    except Exception as e:
        log_process(f"❌ ElevenLabs TTS failed: {e}", overall_start)
        return {"error": f"TTS failed: {str(e)}"}

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

    # 3. TTS
    try:
        audio_stream = elevenlabs_client.text_to_speech.convert(
            text=agent_response,
            voice_id="ulTHPKT60YxEfyrVgZFh",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            )
        audio_bytes = b"".join(audio_stream)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        output_filename = f"output_{abs(hash(agent_response)) % (10 ** 8)}.mp3"
        output_path = os.path.join(DOWNLOAD_DIR, output_filename)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        log_process(f"✓ Output audio saved: {output_path}", overall_start)
    except Exception as e:
        log_process(f"❌ ElevenLabs TTS failed: {e}", overall_start)
        return {"error": f"TTS failed: {str(e)}"}

    return {
        "transcript": text,
        "agent_response": agent_response,
        "audio_base64": audio_base64,
        "output_audio_path": output_path
    }
