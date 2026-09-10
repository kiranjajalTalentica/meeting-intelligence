<script setup lang="ts">
/**
 * AudioRecorder Component
 *
 * Records microphone audio using the browser's built-in MediaRecorder API
 * (no external libraries), then sends it to the backend for transcription.
 *
 * Also supports uploading a pre-recorded audio file.
 *
 * On success, emits the transcribed text so the parent can drop it into
 * the transcript box and run the intelligence pipeline.
 */
import { ref, onUnmounted } from 'vue'
import { transcribeAudio } from '../services/api'

const props = defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  transcribed: [text: string]
}>()

const isRecording = ref(false)
const isTranscribing = ref(false)
const status = ref('')
const elapsed = ref(0)

let mediaRecorder: MediaRecorder | null = null
let chunks: Blob[] = []
let stream: MediaStream | null = null
let timer: ReturnType<typeof setInterval> | null = null

async function startRecording() {
  status.value = ''
  chunks = []
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    status.value = 'Microphone access denied or unavailable.'
    return
  }

  mediaRecorder = new MediaRecorder(stream)
  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data)
  }
  mediaRecorder.onstop = handleStop

  mediaRecorder.start()
  isRecording.value = true
  elapsed.value = 0
  timer = setInterval(() => (elapsed.value += 1), 1000)
}

function stopRecording() {
  if (mediaRecorder && isRecording.value) {
    mediaRecorder.stop()
    isRecording.value = false
    if (timer) clearInterval(timer)
  }
}

async function handleStop() {
  // Release the microphone
  stream?.getTracks().forEach((t) => t.stop())
  stream = null

  const blob = new Blob(chunks, { type: 'audio/webm' })
  await sendForTranscription(blob, 'recording.webm')
}

async function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    await sendForTranscription(file, file.name)
  }
  input.value = '' // reset so the same file can be re-selected
}

async function sendForTranscription(blob: Blob, filename: string) {
  isTranscribing.value = true
  status.value = 'Transcribing audio... (first run downloads the model)'
  try {
    const result = await transcribeAudio(
      blob,
      `mtg-${Date.now()}`,
      filename
    )
    if (result.transcript.trim()) {
      status.value = `Transcribed ${result.duration}s of ${result.language} audio.`
      emit('transcribed', result.transcript)
    } else {
      status.value = 'No speech detected in the audio.'
    }
  } catch (err: any) {
    status.value =
      'Transcription failed: ' +
      (err?.response?.data?.detail || err.message || 'unknown error')
  } finally {
    isTranscribing.value = false
  }
}

function fmt(sec: number) {
  const m = Math.floor(sec / 60)
    .toString()
    .padStart(2, '0')
  const s = (sec % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

onUnmounted(() => {
  stream?.getTracks().forEach((t) => t.stop())
  if (timer) clearInterval(timer)
})

</script>

<template>
  <section class="recorder">
    <div class="controls">
      <button
        v-if="!isRecording"
        class="record"
        @click="startRecording"
        :disabled="disabled || isTranscribing"
      >
        Record
      </button>
      <button
        v-else
        class="stop"
        @click="stopRecording"
      >
        Stop
      </button>

      <span v-if="isRecording" class="rec-indicator">
        <span class="dot"></span> Recording {{ fmt(elapsed) }}
      </span>

      <label class="upload" :class="{ disabled: disabled || isTranscribing }">
        Upload audio
        <input
          type="file"
          accept="audio/*"
          @change="onFileSelected"
          :disabled="disabled || isTranscribing"
          hidden
        />
      </label>
    </div>

    <div v-if="status" class="status">{{ status }}</div>
  </section>
</template>

<style scoped>
.recorder {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

button {
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  color: white;
}

button.record {
  background: #dc2626;
}

button.stop {
  background: #374151;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.rec-indicator {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: #dc2626;
}

.dot {
  width: 10px;
  height: 10px;
  background: #dc2626;
  border-radius: 50%;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.upload {
  font-size: 0.85rem;
  color: #4f46e5;
  cursor: pointer;
  text-decoration: underline;
}

.upload.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.status {
  font-size: 0.85rem;
  color: #6b7280;
}
</style>
