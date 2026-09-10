<script setup lang="ts">
/**
 * App.vue — Main application shell.
 *
 * Coordinates between transcript input and insights display.
 * Manages loading/error state and checks LLM connectivity on startup.
 */
import { ref, onMounted } from 'vue'
import TranscriptInput from './components/TranscriptInput.vue'
import InsightsDisplay from './components/InsightsDisplay.vue'
import { analyzeMeeting, checkLlmStatus } from './services/api'
import type { MeetingInsights } from './types/meeting'

const insights = ref<MeetingInsights | null>(null)
const loading = ref(false)
const error = ref('')

// LLM connection status shown as a badge in the header
const llmConnected = ref<boolean | null>(null) // null = unknown/checking
const llmProvider = ref('')

async function refreshLlmStatus() {
  try {
    const status = await checkLlmStatus()
    llmConnected.value = status.status === 'connected'
    llmProvider.value = status.provider
  } catch {
    llmConnected.value = false
    llmProvider.value = ''
  }
}

onMounted(refreshLlmStatus)

async function handleSubmit(transcript: string) {
  loading.value = true
  error.value = ''
  insights.value = null

  try {
    insights.value = await analyzeMeeting({
      meeting_id: `mtg-${Date.now()}`,
      transcript,
    })
  } catch (err: any) {
    error.value =
      err?.response?.data?.detail || err.message || 'Analysis failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="app">
    <header>
      <div class="title-row">
        <h1>Meeting Intelligence</h1>
        <span
          class="llm-badge"
          :class="{
            connected: llmConnected === true,
            disconnected: llmConnected === false,
            checking: llmConnected === null,
          }"
          @click="refreshLlmStatus"
          title="Click to re-check LLM connection"
        >
          <template v-if="llmConnected === null">Checking LLM...</template>
          <template v-else-if="llmConnected">LLM Connected</template>
          <template v-else>LLM Offline</template>
        </span>
      </div>
      <p>Paste a meeting transcript and extract structured insights.</p>
      <p v-if="llmConnected === false" class="warn">
        The LLM provider isn't reachable. Start LM Studio (or configure Gemini)
        and click the badge to re-check.
      </p>
    </header>

    <main>
      <TranscriptInput :disabled="loading" @submit="handleSubmit" />

      <div v-if="loading" class="status">
        Analyzing transcript... this can take a minute on a local model.
      </div>
      <div v-if="error" class="status error">{{ error }}</div>

      <InsightsDisplay v-if="insights" :insights="insights" />
    </main>
  </div>
</template>

<style>
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin: 0;
  padding: 0;
  background: #ffffff;
  color: #1f2937;
}

.app {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

header {
  margin-bottom: 2rem;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

header h1 {
  margin: 0;
  color: #111827;
}

header p {
  color: #6b7280;
  margin-top: 0.25rem;
}

header p.warn {
  color: #b45309;
}

.llm-badge {
  font-size: 0.75rem;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  cursor: pointer;
  user-select: none;
}

.llm-badge.connected {
  background: #dcfce7;
  color: #15803d;
}

.llm-badge.disconnected {
  background: #fee2e2;
  color: #b91c1c;
}

.llm-badge.checking {
  background: #f3f4f6;
  color: #6b7280;
}

main {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.status {
  padding: 0.75rem;
  border-radius: 4px;
  background: #eef2ff;
  color: #4338ca;
}

.status.error {
  background: #fef2f2;
  color: #dc2626;
}
</style>
