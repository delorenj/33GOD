# HeyMa - Technical Implementation Guide

## Overview

HeyMa is a voice-controlled AI assistant system with real-time speech-to-text transcription, natural language processing, and text-to-speech response capabilities. It features three main components: WhisperLiveKit (Python transcription server), TonnyTray (Tauri desktop app), and a Chrome extension for browser-based transcription.

## Implementation Details

**Language**: Python 3.10 (backend), Rust + TypeScript (desktop), JavaScript (extension)
**Core Frameworks**: FastAPI (HTTP/WebSocket server), Tauri (desktop), React (UI)
**Speech Recognition**: WhisperLiveKit (faster-whisper)
**TTS**: ElevenLabs API
**Package Manager**: uv (Python), npm (Node.js)
**Audio**: pyaudio (Python), cpal + rodio (Rust)

### Key Technologies

**Backend (WhisperLiveKit)**:
- **FastAPI**: Async HTTP server with WebSocket support
- **faster-whisper**: Optimized Whisper inference
- **uvicorn**: ASGI server
- **scipy/numpy**: Audio processing

**Desktop (TonnyTray)**:
- **Tauri**: Cross-platform desktop framework (Rust backend + web frontend)
- **React + TypeScript**: UI layer
- **Zustand**: State management
- **cpal**: Cross-platform audio I/O
- **rodio**: Audio playback
- **SQLite**: Transcription history

**Chrome Extension**:
- **WebSocket**: Real-time connection to WhisperLiveKit
- **Chrome APIs**: tabs, storage, permissions

## Architecture & Design Patterns

### Multi-Component Architecture

```
┌─────────────────────────────────────────────────────┐
│                User Speech Input                    │
└──────────────────┬──────────────────────────────────┘
                   │
    ┌──────────────▼─────────────────┐
    │  WhisperLiveKit Server          │
    │  (Python/FastAPI)               │
    │  - Speech-to-text               │
    │  - WebSocket API (port 8888)    │
    └──────────────┬─────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
    ┌────▼────────┐    ┌──────▼──────────┐
    │ TonnyTray   │    │ Chrome Extension│
    │ (Tauri App) │    │ (Browser)       │
    └────┬────────┘    └──────┬──────────┘
         │                    │
         └─────────┬──────────┘
                   │
        ┌──────────▼──────────────┐
        │   Node-RED Webhook      │
        │   (Workflow Automation) │
        └──────────┬──────────────┘
                   │
        ┌──────────▼──────────────┐
        │   ElevenLabs TTS        │
        │   (Voice Response)      │
        └──────────┬──────────────┘
                   │
        ┌──────────▼──────────────┐
        │   Speaker Output        │
        └─────────────────────────┘
```

### WhisperLiveKit Server

```python
# whisperlivekit/basic_server.py
from fastapi import FastAPI, WebSocket
from faster_whisper import WhisperModel
import asyncio
import numpy as np

app = FastAPI()

class TranscriptionService:
    def __init__(self):
        # Load Whisper model (runs on CPU or GPU)
        self.model = WhisperModel(
            "base",  # Model size: tiny, base, small, medium, large-v3
            device="cpu",
            compute_type="int8"
        )

    async def transcribe_stream(
        self,
        audio_chunks: asyncio.Queue
    ) -> AsyncIterator[str]:
        """Stream transcription results as audio arrives"""
        buffer = []

        while True:
            chunk = await audio_chunks.get()
            if chunk is None:  # End of stream
                break

            buffer.append(chunk)

            # Process when buffer reaches threshold
            if len(buffer) >= 10:
                audio = np.concatenate(buffer)
                segments, info = self.model.transcribe(
                    audio,
                    beam_size=5,
                    language="en"
                )

                for segment in segments:
                    yield segment.text

                buffer.clear()

@app.websocket("/asr")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    service = TranscriptionService()
    audio_queue = asyncio.Queue()

    # Background task for transcription
    async def process_audio():
        async for text in service.transcribe_stream(audio_queue):
            # Send transcription to client
            await websocket.send_json({
                "type": "transcription",
                "text": text,
                "timestamp": datetime.utcnow().isoformat()
            })

    transcription_task = asyncio.create_task(process_audio())

    try:
        while True:
            # Receive binary audio chunks
            data = await websocket.receive_bytes()

            # Convert to numpy array (16kHz, 16-bit PCM)
            audio_chunk = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

            await audio_queue.put(audio_chunk)
    except WebSocketDisconnect:
        await audio_queue.put(None)  # Signal end
        await transcription_task
```

### TonnyTray Desktop App (Tauri)

**Rust Backend** (`src-tauri/src/lib.rs`):
```rust
use tauri::{Manager, State};
use tokio::sync::Mutex;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

struct AppState {
    audio_stream: Mutex<Option<cpal::Stream>>,
    transcription_client: Mutex<Option<WebSocketClient>>,
}

#[tauri::command]
async fn start_recording(
    state: State<'_, AppState>,
    server_url: String
) -> Result<(), String> {
    let host = cpal::default_host();
    let device = host.default_input_device()
        .ok_or("No input device available")?;

    let config = device.default_input_config()
        .map_err(|e| e.to_string())?;

    // Connect to WhisperLiveKit via WebSocket
    let ws_client = WebSocketClient::connect(&server_url).await
        .map_err(|e| e.to_string())?;

    let client_clone = ws_client.clone();

    // Create audio stream
    let stream = device.build_input_stream(
        &config.into(),
        move |data: &[f32], _: &cpal::InputCallbackInfo| {
            // Convert to 16-bit PCM
            let pcm: Vec<i16> = data.iter()
                .map(|&sample| (sample * 32768.0) as i16)
                .collect();

            // Send to WebSocket
            let bytes = pcm.as_slice().align_to::<u8>().1;
            client_clone.send_binary(bytes.to_vec());
        },
        |err| eprintln!("Audio stream error: {}", err),
        None
    ).map_err(|e| e.to_string())?;

    stream.play().map_err(|e| e.to_string())?;

    // Store state
    *state.audio_stream.lock().await = Some(stream);
    *state.transcription_client.lock().await = Some(ws_client);

    Ok(())
}

#[tauri::command]
async fn stop_recording(state: State<'_, AppState>) -> Result<(), String> {
    if let Some(stream) = state.audio_stream.lock().await.take() {
        drop(stream);  // Stops the stream
    }

    if let Some(client) = state.transcription_client.lock().await.take() {
        client.close().await;
    }

    Ok(())
}

#[tauri::command]
async fn send_to_elevenlabs(
    text: String,
    api_key: String,
    voice_id: String
) -> Result<Vec<u8>, String> {
    let client = reqwest::Client::new();

    let response = client
        .post(format!("https://api.elevenlabs.io/v1/text-to-speech/{}", voice_id))
        .header("xi-api-key", api_key)
        .json(&serde_json::json!({
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }))
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let audio_bytes = response.bytes().await
        .map_err(|e| e.to_string())?;

    Ok(audio_bytes.to_vec())
}
```

**React Frontend** (`src/App.tsx`):
```typescript
import { useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { listen } from '@tauri-apps/api/event';

interface Transcription {
    text: string;
    timestamp: string;
}

function App() {
    const [isRecording, setIsRecording] = useState(false);
    const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);

    useEffect(() => {
        // Listen for transcription events from Rust backend
        const unlisten = listen<Transcription>('transcription', (event) => {
            setTranscriptions(prev => [...prev, event.payload]);
        });

        return () => {
            unlisten.then(fn => fn());
        };
    }, []);

    const handleStartRecording = async () => {
        try {
            await invoke('start_recording', {
                serverUrl: 'ws://localhost:8888/asr'
            });
            setIsRecording(true);
        } catch (error) {
            console.error('Failed to start recording:', error);
        }
    };

    const handleStopRecording = async () => {
        try {
            await invoke('stop_recording');
            setIsRecording(false);
        } catch (error) {
            console.error('Failed to stop recording:', error);
        }
    };

    const handleSendToN8N = async (text: string) => {
        await fetch('https://nodered.delo.sh/webhook/transcription', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                timestamp: new Date().toISOString()
            })
        });
    };

    return (
        <div className="app">
            <button
                onClick={isRecording ? handleStopRecording : handleStartRecording}
            >
                {isRecording ? 'Stop Recording' : 'Start Recording'}
            </button>

            <div className="transcriptions">
                {transcriptions.map((t, i) => (
                    <div key={i} className="transcription">
                        <p>{t.text}</p>
                        <small>{new Date(t.timestamp).toLocaleString()}</small>
                        <button onClick={() => handleSendToN8N(t.text)}>
                            Send to Node-RED
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

### Auto-Type Client

```python
# scripts/auto_type_client.py
import asyncio
import websockets
import pyautogui
import json

async def auto_type_transcription(server_url: str):
    """Types transcriptions into active window"""
    uri = f"ws://{server_url}/asr"

    async with websockets.connect(uri) as websocket:
        print("Connected to WhisperLiveKit. Speak to type...")

        # Send audio from microphone
        audio_task = asyncio.create_task(
            stream_microphone_to_websocket(websocket)
        )

        # Receive transcriptions
        while True:
            message = await websocket.recv()
            data = json.loads(message)

            if data["type"] == "transcription":
                text = data["text"]
                print(f"Typing: {text}")

                # Type into active window
                pyautogui.typewrite(text, interval=0.05)
                pyautogui.press('space')

async def stream_microphone_to_websocket(websocket):
    """Capture audio and send to WebSocket"""
    import pyaudio

    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    p = pyaudio.PyAudio()

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    try:
        while True:
            data = stream.read(CHUNK)
            await websocket.send(data)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    asyncio.run(auto_type_transcription("localhost:8888"))
```

## Configuration

### WhisperLiveKit Config

```bash
# Environment variables
WHISPER_MODEL=base  # tiny, base, small, medium, large-v3
WHISPER_DEVICE=cpu  # cpu or cuda
WHISPER_COMPUTE_TYPE=int8  # int8, float16, float32
SERVER_HOST=0.0.0.0
SERVER_PORT=8888
```

### TonnyTray Config

```json
// ~/.config/tonnytray/config.json
{
  "whisper_server_url": "ws://localhost:8888/asr",
  "elevenlabs_api_key": "your_api_key",
  "elevenlabs_voice_id": "21m00Tcm4TlvDq8ikWAM",
  "node_red_webhook": "https://nodered.delo.sh/webhook/transcription",
  "auto_start_recording": false,
  "notification_sounds": true
}
```

## Integration Points

### Node-RED Webhook Integration

```bash
# Send transcription to Node-RED
./bin/n8n-webhook --n8n-webhook https://nodered.delo.sh/webhook/transcription
```

Node-RED flow processes transcription and can:
- Trigger automation workflows
- Store in database
- Send notifications
- Generate AI responses via ElevenLabs

### Bloodbank Event Publishing

```python
# Publish transcription events to Bloodbank
async def publish_transcription_event(text: str):
    from bloodbank import Publisher

    publisher = Publisher()
    await publisher.publish(
        routing_key="transcription.voice.completed",
        body={
            "event_type": "transcription.voice.completed",
            "source": "whisperlivekit",
            "data": {
                "text": text,
                "language": "en",
                "confidence": 0.95,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

## Performance Characteristics

### Transcription Latency

- **Model Loading**: 3-10 seconds (depends on model size)
- **Streaming Latency**: 200-500ms per utterance
- **Accuracy**: 85-95% (depends on audio quality and model size)

### Resource Usage

- **Memory**: 500MB-2GB (depends on Whisper model)
- **CPU**: 20-50% (CPU inference)
- **GPU**: 10-30% (CUDA inference, much faster)
- **Network**: ~32kbps (16kHz 16-bit audio stream)

## Edge Cases & Troubleshooting

### Audio Device Issues

```bash
# List available audio devices
./bin/auto-type --list-devices

# Manually select device
./bin/auto-type --device 6
```

### Server Connection Failures

```python
# Auto-reconnect with exponential backoff
async def resilient_connection(server_url: str):
    retry_count = 0
    max_retries = 10

    while retry_count < max_retries:
        try:
            async with websockets.connect(server_url) as ws:
                await handle_transcriptions(ws)
                retry_count = 0  # Reset on success
        except Exception as e:
            backoff = min(60, 2 ** retry_count)
            print(f"Connection failed. Retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            retry_count += 1
```

## Related Components

- **Bloodbank**: Event bus for transcription events
- **Candystore**: Event storage and audit trail
- **Node-RED**: Workflow automation and AI response generation

---

**Quick Reference**:
- GitHub: `33GOD/HeyMa`
- WhisperLiveKit Port: 8888
- Package Manager: uv (Python), npm (Node.js)
- Docs: `QUICKSTART.md`, `TonnyTray/README.md`
