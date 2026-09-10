<script setup lang="ts">
/**
 * TranscriptInput Component
 *
 * Ways to get a transcript:
 *  1. Record from the microphone (AudioRecorder) — auto-transcribed
 *  2. Upload an audio file (AudioRecorder) — auto-transcribed
 *  3. Load the bundled sample transcript
 *  4. Paste/type directly
 *
 * Once there's a transcript, "Process Meeting" runs the intelligence pipeline.
 */
import { ref } from 'vue'
import AudioRecorder from './AudioRecorder.vue'
import { fetchSampleTranscript } from '../services/api'

const props = defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  submit: [transcript: string]
}>()

const transcript = ref('')
const loadingSample = ref(false)

function handleSubmit() {
  if (transcript.value.trim() && !props.disabled) {
    emit('submit', transcript.value)
  }
}

async function loadSample() {
  loadingSample.value = true
  try {
    transcript.value = await fetchSampleTranscript()
  } catch {
    transcript.value = 'Could not load sample transcript from the backend.'
  } finally {
    loadingSample.value = false
  }
}

// When audio is transcribed, drop the text into the box
function onTranscribed(text: string) {
  transcript.value = text
}
</script>

<template>
  <section class="transcript-input">
    <div class="header-row">
      <h2>Meeting Transcript</h2>
      <button
        class="secondary"
        @click="loadSample"
        :disabled="loadingSample || disabled"
      >
        {{ loadingSample ? 'Loading...' : 'Load Sample' }}
      </button>
    </div>

    <!-- Record or upload audio to auto-generate the transcript -->
    <AudioRecorder :disabled="disabled" @transcribed="onTranscribed" />

    <textarea
      v-model="transcript"
      placeholder="Record above, upload audio, load the sample, or paste your transcript here..."
      rows="14"
      :disabled="disabled"
    ></textarea>

    <div class="footer-row">
      <span class="char-count">{{ transcript.length }} characters</span>
      <button
        class="primary"
        @click="handleSubmit"
        :disabled="!transcript.trim() || disabled"
      >
        Process Meeting
      </button>
    </div>
  </section>
</template>

<style scoped>
.transcript-input {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.header-row,
.footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-row h2 {
  margin: 0;
}

.char-count {
  font-size: 0.8rem;
  color: #9ca3af;
}

textarea {
  width: 100%;
  padding: 0.75rem;
  font-family: inherit;
  font-size: 0.9rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  resize: vertical;
  box-sizing: border-box;
}

button {
  padding: 0.6rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

button.primary {
  background: #4f46e5;
  color: white;
}

button.secondary {
  background: #e5e7eb;
  color: #374151;
  padding: 0.4rem 1rem;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
