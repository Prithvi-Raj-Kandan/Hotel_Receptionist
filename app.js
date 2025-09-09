const micBtn = document.getElementById("mic-btn")
const micIcon = document.getElementById("mic-icon")
const micVisualizer = document.getElementById("mic-visualizer")
const chatArea = document.getElementById("chat-area")

let isRecording = false
let mediaRecorder = null
let audioChunks = []
let currentPlaceholderId = null

micBtn.addEventListener("click", () => {
  if (!isRecording) startRecording()
  else stopRecording()
})

async function startRecording() {
  isRecording = true
  micIcon.style.display = "none"
  micVisualizer.style.display = "flex"

  // Add listening placeholder
  currentPlaceholderId = "listening-" + Date.now()
  addMessage("Listening...", "placeholder", currentPlaceholderId)

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    })

    let mimeType = "audio/webm;codecs=opus"
    if (!MediaRecorder.isTypeSupported(mimeType)) {
      mimeType = "audio/webm"
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = "audio/mp4"
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = "" // Let browser choose
        }
      }
    }

    mediaRecorder = new MediaRecorder(stream, {
      mimeType,
      audioBitsPerSecond: 128000,
    })
    audioChunks = []

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        console.log("[v0] Audio chunk received:", e.data.size, "bytes")
        audioChunks.push(e.data)
      }
    }

    mediaRecorder.start(100) // Collect data every 100ms for better reliability
    console.log("[v0] Recording started with mime type:", mediaRecorder.mimeType)
  } catch (err) {
    console.error("Microphone access error:", err)
    replacePlaceholder(currentPlaceholderId, "Microphone access denied or not available.", "bot")
    stopRecording(true)
  }
}

function stopRecording(abortOnly = false) {
  isRecording = false
  micIcon.style.display = ""
  micVisualizer.style.display = "none"

  if (!mediaRecorder) return

  if (abortOnly) {
    try {
      mediaRecorder.stream.getTracks().forEach((t) => t.stop())
    } catch (e) {
      console.error("Error stopping tracks:", e)
    }
    mediaRecorder = null
    return
  }

  if (mediaRecorder.state !== "inactive") {
    mediaRecorder.stop()
    mediaRecorder.onstop = () => {
      const actualMimeType = mediaRecorder.mimeType || "audio/webm"
      console.log("[v0] Creating blob with type:", actualMimeType)
      console.log("[v0] Total audio chunks:", audioChunks.length)

      const audioBlob = new Blob(audioChunks, { type: actualMimeType })
      console.log("[v0] Audio blob created:", audioBlob.size, "bytes")

      if (audioBlob.size > 0) {
        // Small delay to ensure blob is fully created
        setTimeout(() => {
          sendAudioToVoiceBot(audioBlob, actualMimeType)
        }, 100)
      } else {
        console.error("[v0] Audio blob is empty")
        replacePlaceholder(currentPlaceholderId, "Recording failed - no audio data captured.", "bot")
      }

      try {
        mediaRecorder.stream.getTracks().forEach((t) => t.stop())
      } catch (e) {
        console.error("Error stopping tracks:", e)
      }
      mediaRecorder = null
    }
  }
}

async function sendAudioToVoiceBot(audioBlob, mimeType) {
  const formData = new FormData()

  let filename = "audio.webm"
  if (mimeType.includes("mp4")) {
    filename = "audio.mp4"
  } else if (mimeType.includes("wav")) {
    filename = "audio.wav"
  }

  formData.append("file", audioBlob, filename)
  console.log("[v0] Sending audio file:", filename, "Size:", audioBlob.size, "bytes")

  // Replace listening with thinking
  replacePlaceholder(currentPlaceholderId, "Thinking...", "placeholder")

  try {
    const response = await fetch("http://127.0.0.1:8000/voicebot", {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error("[v0] Server error:", response.status, errorText)
      replacePlaceholder(currentPlaceholderId, "VoiceBot request failed. Please try again.", "bot")
      return
    }

    const data = await response.json()
    console.log("[v0] VoiceBot response:", data)

    // FIXED: Add user message first, then bot response
    const userTranscript = data?.transcript || "[Unrecognized speech]"
    const botResponse = data?.agent_response || "[No response]"

    // Replace placeholder with user message first
    replacePlaceholder(currentPlaceholderId, userTranscript, "user")

    // Then add bot response
    setTimeout(() => {
      addMessage(botResponse, "bot")

      // Play audio response if available
      if (data?.audio_base64) {
        playBase64Audio(data.audio_base64)
      }
    }, 300) // Small delay for better UX
  } catch (err) {
    console.error("VoiceBot API error:", err)
    replacePlaceholder(currentPlaceholderId, "Error contacting VoiceBot backend. Please check your connection.", "bot")
  }
}

function playBase64Audio(base64) {
  try {
    const byteCharacters = atob(base64)
    const byteNumbers = new Array(byteCharacters.length)
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i)
    }
    const byteArray = new Uint8Array(byteNumbers)
    const blob = new Blob([byteArray], { type: "audio/mp3" })

    const audio = new Audio(URL.createObjectURL(blob))
    audio.onloadeddata = () => {
      audio.play().catch((e) => {
        console.error("Audio playback failed:", e)
        addMessage("Audio playback failed. Please check your speakers.", "bot")
      })
    }
    audio.onerror = () => {
      console.error("Audio loading failed")
      addMessage("Audio loading failed.", "bot")
    }
  } catch (err) {
    console.error("Audio processing failed:", err)
    addMessage("Audio processing failed.", "bot")
  }
}

function addMessage(text, sender, placeholderId = null) {
  const msg = document.createElement("div")
  msg.className = `message ${sender}`
  msg.textContent = text
  if (placeholderId) {
    msg.dataset.placeholderId = placeholderId
  }
  chatArea.appendChild(msg)
  chatArea.scrollTop = chatArea.scrollHeight
}

function replacePlaceholder(placeholderId, newText, newSender) {
  const placeholder = chatArea.querySelector(`[data-placeholder-id="${placeholderId}"]`)
  if (placeholder) {
    placeholder.textContent = newText
    placeholder.className = `message ${newSender}`
    if (newSender !== "placeholder") {
      placeholder.removeAttribute("data-placeholder-id")
    }
  } else {
    // Fallback: add new message if placeholder not found
    addMessage(newText, newSender)
  }
}

// Add initial welcome message
document.addEventListener("DOMContentLoaded", () => {
  addMessage("I am your receptionist. I can help you with anything related to the hotel. Place your queries and I will assist you.", "bot")
})
