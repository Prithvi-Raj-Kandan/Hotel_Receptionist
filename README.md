# ProjectVoiceBot 🎤🤖

A sophisticated voice-enabled AI assistant that combines speech-to-text, large language model processing, and text-to-speech capabilities to create a seamless conversational experience.

## 🌟 Features

- **🎤 Voice Input**: Real-time audio recording with microphone support
- **🗣️ Speech-to-Text**: Powered by Deepgram's Nova-2 model for accurate transcription
- **🧠 AI Processing**: Llama 3.1 70B model for intelligent responses via Hugging Face
- **🔊 Text-to-Speech**: ElevenLabs integration for natural voice synthesis
- **💬 Conversation Memory**: Maintains context across conversation sessions
- **🎨 Modern UI**: Clean, responsive web interface with real-time visual feedback
- **⚡ Fast Performance**: Optimized backend with detailed performance logging

## 🏗️ Architecture

```
Frontend (HTML/CSS/JS) ←→ Backend (FastAPI) ←→ External APIs
    ↓                           ↓                    ↓
Voice Recording           Speech Processing      Deepgram STT
Chat Interface           LLM Integration       Llama 3.1 70B
Audio Playback          TTS Generation        ElevenLabs TTS
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js (for serving frontend)
- Microphone access
- API keys for external services

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ProjectVoiceBot
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv botenv

# Activate virtual environment
# Windows
botenv\Scripts\activate
# macOS/Linux
source botenv/bin/activate
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the `backend` directory:

```env
DEEPGRAM_API_KEY=your_deepgram_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

**Note**: The Hugging Face token is automatically loaded from your Cursor MCP configuration.

### 5. Start the Backend

```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 6. Serve the Frontend

```bash
cd frontend
# Using Python's built-in server
python -m http.server 8080

# Or using Node.js http-server
npx http-server -p 8080
```

### 7. Open Your Browser

Navigate to `http://localhost:8080` and grant microphone permissions when prompted.

## 🔧 Configuration

### API Keys Required

1. **Deepgram API Key**: For speech-to-text transcription
   - Sign up at [Deepgram](https://deepgram.com/)
   - Get your API key from the dashboard

2. **ElevenLabs API Key**: For text-to-speech synthesis
   - Sign up at [ElevenLabs](https://elevenlabs.io/)
   - Get your API key from the dashboard

3. **Hugging Face Token**: For Llama 3.1 70B access
   - Automatically configured via Cursor MCP
   - Ensure you have access to the Llama 3.1 70B model

### Model Configuration

- **STT Model**: Deepgram Nova-2 (16kHz, mono audio)
- **LLM Model**: Meta Llama 3.1 70B via Hugging Face
- **TTS Model**: ElevenLabs Monolingual v1 with "Bill" voice

## 📱 Usage

### Voice Interaction

1. **Click the microphone button** to start recording
2. **Speak your question or request** clearly
3. **Click again to stop recording** and process your audio
4. **Listen to the AI response** as it's synthesized and played back

### Text Input

1. **Type your message** in the chat input field
2. **Press Enter** or click send to submit
3. **Receive AI response** with audio playback

### Conversation Management

- The system maintains conversation context for more coherent responses
- Use the `/reset-conversation` endpoint to clear conversation history
- View conversation history via the `/conversation` endpoint

## 🛠️ API Endpoints

### Backend API (FastAPI)

- `POST /stt` - Speech-to-text conversion
- `POST /llm` - Language model processing
- `POST /tts` - Text-to-speech synthesis
- `GET /conversation` - Get conversation history
- `POST /reset-conversation` - Reset conversation

### Request/Response Format

```json
// STT Request
POST /stt
Content-Type: multipart/form-data
file: audio_file

// LLM Request
POST /llm
{
  "prompt": "Your question here"
}

// TTS Request
POST /tts
{
  "text": "Text to synthesize"
}
```

## 📁 Project Structure

```
ProjectVoiceBot/
├── backend/
│   ├── main.py              # FastAPI backend server
│   ├── requirements.txt     # Python dependencies
│   ├── uploads/            # Temporary audio uploads
│   └── downloads/          # Generated audio files
├── frontend/
│   ├── index.html          # Main HTML page
│   ├── app.js              # Frontend JavaScript logic
│   └── styles.css          # CSS styling
├── botenv/                 # Python virtual environment
└── README.md               # This file
```

## 🔍 Troubleshooting

### Common Issues

1. **Microphone Access Denied**
   - Ensure your browser has microphone permissions
   - Check if other applications are using the microphone

2. **API Key Errors**
   - Verify all API keys are correctly set in `.env`
   - Check API key validity and quotas

3. **Audio Playback Issues**
   - Ensure browser supports the audio format
   - Check system volume and audio settings

4. **CORS Errors**
   - Backend is configured to allow all origins
   - Ensure frontend and backend ports are correct

### Performance Optimization

- The system logs detailed performance metrics for each operation
- Monitor API response times in the backend console
- Consider adjusting audio quality settings for better performance

## 🚧 Development

### Adding New Features

1. **New AI Models**: Modify the model initialization in `main.py`
2. **Additional Voices**: Update the TTS configuration in the `tts` endpoint
3. **UI Enhancements**: Modify the frontend files in the `frontend/` directory

### Testing

- Test individual endpoints using tools like Postman or curl
- Monitor backend logs for detailed operation tracking
- Use the conversation reset endpoint to test fresh interactions

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the troubleshooting section above
- Review the backend logs for error details
- Ensure all API keys are valid and have sufficient quotas

## 🙏 Acknowledgments

- **Deepgram** for speech-to-text capabilities
- **Meta** for the Llama 3.1 70B language model
- **ElevenLabs** for text-to-speech synthesis
- **Hugging Face** for model hosting and inference
- **FastAPI** for the robust backend framework

---

**Happy Voice Botting! 🎤✨**
