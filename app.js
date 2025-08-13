const micBtn = document.getElementById('mic-btn');
const micIcon = document.getElementById('mic-icon');
const chatArea = document.getElementById('chat-area');
const micVisualizer = document.getElementById('mic-visualizer');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');

let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

micBtn.addEventListener('click', () => {
    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
});

sendBtn.addEventListener('click', sendPromptFromInput);
chatInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') sendPromptFromInput();
});

async function startRecording() {
    isRecording = true;
    micIcon.style.display = 'none';
    micVisualizer.style.display = 'flex';
    addMessage('Listening...', 'bot');

    // Request microphone access and start recording
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                audioChunks.push(e.data);
            }
        };
        mediaRecorder.start();
    } catch (err) {
        alert('Microphone access denied or not available.');
        stopRecording();
    }
}

function stopRecording() {
    isRecording = false;
    micIcon.style.display = '';
    micVisualizer.style.display = 'none';
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            sendAudioToBackend(audioBlob);
        };
    }
    // Ensure no placeholder messages are added
}

async function sendPromptFromInput() {
    const prompt = chatInput.value.trim();
    if (!prompt) return;
    addMessage(prompt, 'user');
    chatInput.value = '';
    await sendPromptToLLM(prompt);
}

async function sendAudioToBackend(audioBlob) {
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.webm');
    try {
        const response = await fetch('http://127.0.0.1:8000/stt', {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            const data = await response.json();
            addMessage(data.text, 'user');
            // Now send the transcribed text to the LLM
            await sendPromptToLLM(data.text);
        } else {
            addMessage('Failed to transcribe audio.', 'bot');
        }
    } catch (err) {
        addMessage('Error uploading audio.', 'bot');
        console.error(err);
    }
}

async function sendPromptToLLM(prompt) {
    addMessage('Thinking...', 'bot');
    try {
        const response = await fetch('http://127.0.0.1:8000/llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });
        const data = await response.json();
        // Remove the 'Thinking...' message
        const lastMsg = chatArea.querySelector('.message.bot:last-child');
        if (lastMsg && lastMsg.textContent === 'Thinking...') {
            lastMsg.remove();
        }
        addMessage(data.response || data.error || 'No response', 'bot');
        // Now send the LLM response to TTS
        if (data.response) {
            await sendTextToTTS(data.response);
        }
    } catch (err) {
        addMessage('Error contacting backend.', 'bot');
        console.error(err);
    }
}

async function sendTextToTTS(text) {
    try {
        const response = await fetch('http://127.0.0.1:8000/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        const data = await response.json();
        if (data.audio_base64) {
            playBase64Audio(data.audio_base64);
        }
    } catch (err) {
        addMessage('Error generating audio.', 'bot');
        console.error(err);
    }
}

function playBase64Audio(base64) {
    const audio = new Audio('data:audio/wav;base64,' + base64);
    audio.play();
}

function addMessage(text, sender) {
    const msg = document.createElement('div');
    msg.className = `message ${sender}`;
    msg.textContent = text;
    chatArea.appendChild(msg);
    chatArea.scrollTop = chatArea.scrollHeight;
} 