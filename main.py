from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from pydantic import BaseModel
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
import json
import io
import base64
from pydub import AudioSegment
import time
from deepgram import Deepgram
from elevenlabs import generate, save, set_api_key
import requests
from datetime import datetime

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

# Conversation management
conversation_history = []
personality_context = "You are Athena, a professional business assistant. You are efficient, knowledgeable, and formal. Your answers should be concise and professional. Keep responses business-focused and helpful."

def log_process(message, start_time=None):
    """Log process messages with timestamps"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if start_time:
        elapsed = time.time() - start_time
        print(f"[{timestamp}] {message} (elapsed: {elapsed:.2f}s)")
    else:
        print(f"[{timestamp}] {message}")

def build_conversation_prompt(user_input):
    """Build a context-aware prompt with conversation history"""
    if not conversation_history:
        # First message - just use personality context
        return f"{personality_context}\n\nUser: {user_input}\nAthena:"
    else:
        # Build conversation history (only real conversation, not generated)
        # Only include actual user messages and Athena responses from history
        recent_messages = conversation_history[-4:]  # Last 4 messages for context
        history_parts = []
        
        for msg in recent_messages:
            if msg['role'] in ['User', 'Athena']:
                history_parts.append(f"{msg['role']}: {msg['content']}")
        
        if history_parts:
            history_text = "\n".join(history_parts)
            return f"{personality_context}\n\n{history_text}\nUser: {user_input}\nAthena:"
        else:
            return f"{personality_context}\n\nUser: {user_input}\nAthena:"

def add_to_conversation(role, content):
    """Add message to conversation history"""
    conversation_history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    # Keep only last 10 messages to prevent context overflow
    if len(conversation_history) > 10:
        conversation_history.pop(0)

# Initialize Deepgram client
log_process("Initializing Deepgram client...")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY environment variable not set")
deepgram = Deepgram(DEEPGRAM_API_KEY)
log_process("✓ Deepgram client initialized")

# Initialize Hugging Face client for Llama 3.1 70B
log_process("Initializing Hugging Face client...")
# Get HF token from mcp.json
mcp_path = os.path.expanduser("~/.cursor/mcp.json")
try:
    with open(mcp_path, "r") as f:
        mcp_config = json.load(f)
    HF_TOKEN = mcp_config["mcpServers"]["hf-mcp-server"]["headers"]["Authorization"].replace("Bearer ", "")
    log_process("✓ HF token loaded from mcp.json")
except Exception as e:
    raise ValueError(f"Could not load Hugging Face token from mcp.json: {e}")

llama_client = InferenceClient(
    provider="featherless-ai",
    api_key=HF_TOKEN,
)
log_process("✓ Hugging Face client initialized for Llama 3.1 70B")

# Initialize ElevenLabs
log_process("Initializing ElevenLabs client...")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY environment variable not set")
set_api_key(ELEVENLABS_API_KEY)
log_process("✓ ElevenLabs client initialized")

log_process("🚀 VoiceBot backend ready!")

@app.get("/conversation")
async def get_conversation():
    """Get current conversation history"""
    return {"conversation": conversation_history}

@app.post("/reset-conversation")
async def reset_conversation():
    """Reset conversation history"""
    global conversation_history
    conversation_history = []
    log_process("🔄 Conversation history reset")
    return {"message": "Conversation reset successfully"}

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    start_time = time.time()
    log_process("📁 Audio upload request received", start_time)
    
    filename = file.filename or "audio.webm"
    file_location = os.path.join(UPLOAD_DIR, filename)
    
    log_process("💾 Saving audio file...", start_time)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    log_process(f"✓ Audio saved: {filename}", start_time)
    return {"filename": filename, "status": "saved"} 

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    overall_start = time.time()
    log_process("🎤 STT Request: Starting speech-to-text conversion", overall_start)
    
    # Read audio file
    read_start = time.time()
    log_process("📖 Reading audio file...", overall_start)
    audio_bytes = await file.read()
    read_end = time.time()
    log_process(f"✓ Audio file read ({len(audio_bytes)} bytes)", overall_start)
    
    # Save input audio to uploads
    save_start = time.time()
    log_process("💾 Saving input audio...", overall_start)
    input_path = os.path.join(UPLOAD_DIR, file.filename or "input.webm")
    with open(input_path, "wb") as f:
        f.write(audio_bytes)
    save_end = time.time()
    log_process(f"✓ Input audio saved: {input_path}", overall_start)
    
    # Convert audio format
    convert_start = time.time()
    log_process("🔄 Converting audio format (WebM → WAV)...", overall_start)
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
    audio = audio.set_frame_rate(16000).set_channels(1)
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)
    convert_end = time.time()
    log_process(f"✓ Audio converted to WAV (16kHz, mono)", overall_start)
    
    # Deepgram API call
    api_start = time.time()
    log_process("🌐 Calling Deepgram API for transcription...", overall_start)
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
        api_end = time.time()
        log_process(f"✓ Deepgram transcription completed", overall_start)
        log_process(f"📝 Transcribed text: '{text}'", overall_start)
        
        # Add user message to conversation history
        add_to_conversation("User", text)
        
        # Final timing summary
        total_time = time.time() - overall_start
        breakdown = [
            ("Read", read_end-read_start),
            ("Save", save_end-save_start),
            ("Convert", convert_end-convert_start),
            ("API", api_end-api_start)
        ]
        breakdown.sort(key=lambda x: x[1], reverse=True)
        breakdown_str = ", ".join([f"{name}={duration:.2f}s" for name, duration in breakdown])
        log_process(f"🎯 STT COMPLETE - Total time: {total_time:.2f}s", overall_start)
        log_process(f"   Breakdown (desc): {breakdown_str}")
        
        return {"text": text, "input_audio_path": input_path}
    except Exception as e:
        log_process(f"❌ Deepgram STT failed: {e}", overall_start)
        return {"error": f"STT failed: {str(e)}"}

# LLM request/response models
class LLMRequest(BaseModel):
    prompt: str

@app.post("/llm")
async def llm_response(request: LLMRequest):
    overall_start = time.time()
    log_process("🧠 LLM Request: Starting language processing", overall_start)
    log_process(f"📝 Input prompt: '{request.prompt}'", overall_start)
    
    try:
        # Build context-aware prompt
        prep_start = time.time()
        log_process("🔧 Building context-aware prompt for Llama 3.1 70B...", overall_start)
        context_prompt = build_conversation_prompt(request.prompt)
        prep_end = time.time()
        log_process("✓ Context-aware prompt built", overall_start)
        
        # Llama 3.1 70B API call
        api_start = time.time()
        log_process("🌐 Calling Llama 3.1 70B via Hugging Face...", overall_start)
        result = llama_client.text_generation(
            context_prompt,
            model="meta-llama/Llama-3.1-70B",
            max_new_tokens=150,  # Increased for more natural responses
            temperature=0.8,  # Slightly higher for more personality
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1,
        )
        api_end = time.time()
        log_process(f"✓ Llama 3.1 70B response received", overall_start)
        log_process(f"💬 LLM response: '{result}'", overall_start)
        
        # Add assistant response to conversation history
        add_to_conversation("Athena", result)
        
        # Final timing summary
        total_time = time.time() - overall_start
        breakdown = [
            ("Prep", prep_end-prep_start),
            ("API", api_end-api_start)
        ]
        breakdown.sort(key=lambda x: x[1], reverse=True)
        breakdown_str = ", ".join([f"{name}={duration:.2f}s" for name, duration in breakdown])
        log_process(f"🎯 LLM COMPLETE - Total time: {total_time:.2f}s", overall_start)
        log_process(f"   Breakdown (desc): {breakdown_str}")
        
        return {"response": result}
    except Exception as e:
        log_process(f"❌ Llama 3.1 70B LLM failed: {e}", overall_start)
        return {"error": str(e)}

# TTS request/response models
class TTSRequest(BaseModel):
    text: str

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    overall_start = time.time()
    log_process("🔊 TTS Request: Starting text-to-speech conversion", overall_start)
    log_process(f"📝 Input text: '{request.text}'", overall_start)
    
    # ElevenLabs API call
    api_start = time.time()
    log_process("🌐 Calling ElevenLabs API for speech synthesis...", overall_start)
    try:
        audio = generate(
            text=request.text,  # No truncation - use full response
            voice="Bill",  # Changed to Bill which is available in the account
            model="eleven_monolingual_v1"
        )
        api_end = time.time()
        log_process(f"✓ ElevenLabs audio generated ({len(audio)} bytes)", overall_start)
        
        # Convert to base64
        encode_start = time.time()
        log_process("🔧 Converting audio to base64...", overall_start)
        audio_base64 = base64.b64encode(audio).decode('utf-8')
        encode_end = time.time()
        log_process("✓ Audio encoded to base64", overall_start)
        
        # Save output audio
        save_start = time.time()
        log_process("💾 Saving output audio file...", overall_start)
        output_filename = f"output_{abs(hash(request.text)) % (10 ** 8)}.mp3"
        output_path = os.path.join(DOWNLOAD_DIR, output_filename)
        with open(output_path, "wb") as f:
            f.write(audio)
        save_end = time.time()
        log_process(f"✓ Output audio saved: {output_path}", overall_start)
        
        # Final timing summary
        total_time = time.time() - overall_start
        breakdown = [
            ("API", api_end-api_start),
            ("Encode", encode_end-encode_start),
            ("Save", save_end-save_start)
        ]
        breakdown.sort(key=lambda x: x[1], reverse=True)
        breakdown_str = ", ".join([f"{name}={duration:.2f}s" for name, duration in breakdown])
        log_process(f"🎯 TTS COMPLETE - Total time: {total_time:.2f}s", overall_start)
        log_process(f"   Breakdown (desc): {breakdown_str}")
        log_process("🎵 Ready for audio playback!")
        
        return {"audio_base64": audio_base64, "output_audio_path": output_path}
    except Exception as e:
        log_process(f"❌ ElevenLabs TTS failed: {e}", overall_start)
        return {"error": f"TTS failed: {str(e)}"} 