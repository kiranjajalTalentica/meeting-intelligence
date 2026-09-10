<script setup lang="ts">
/**
 * InsightsDisplay Component
 *
 * Renders the structured meeting insights returned by the API.
 * Each section (summary, topics, decisions, action items, open questions)
 * is displayed in its own block.
 */
import type { MeetingInsights } from '@/types/meeting'

defineProps<{
  insights: MeetingInsights
}>()
</script>

<template>
  <section class="insights">
    <!-- Summary -->
    <div class="insight-block">
      <h3>Summary</h3>
      <p>{{ insights.summary || 'No summary generated.' }}</p>
    </div>

    <!-- Topics -->
    <div class="insight-block">
      <h3>Topics</h3>
      <ul v-if="insights.topics.length">
        <li v-for="topic in insights.topics" :key="topic.title">
          <strong>{{ topic.title }}</strong>: {{ topic.summary }}
        </li>
      </ul>
      <p v-else>No topics detected.</p>
    </div>

    <!-- Decisions -->
    <div class="insight-block">
      <h3>Decisions</h3>
      <ul v-if="insights.decisions.length">
        <li v-for="d in insights.decisions" :key="d.decision">
          <strong>{{ d.decision }}</strong>
          <span v-if="d.reason"> — {{ d.reason }}</span>
        </li>
      </ul>
      <p v-else>No decisions found.</p>
    </div>

    <!-- Action Items -->
    <div class="insight-block">
      <h3>Action Items</h3>
      <ul v-if="insights.action_items.length">
        <li v-for="item in insights.action_items" :key="item.task">
          <strong>{{ item.task }}</strong>
          <span v-if="item.owner"> — Owner: {{ item.owner }}</span>
          <span v-if="item.deadline"> — Due: {{ item.deadline }}</span>
        </li>
      </ul>
      <p v-else>No action items found.</p>
    </div>

    <!-- Open Questions -->
    <div class="insight-block">
      <h3>Open Questions</h3>
      <ul v-if="insights.open_questions.length">
        <li v-for="q in insights.open_questions" :key="q.question">
          <strong>{{ q.question }}</strong>
          <span v-if="q.context"> — {{ q.context }}</span>
        </li>
      </ul>
      <p v-else>No open questions found.</p>
    </div>
  </section>
</template>

<style scoped>
.insights {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.insight-block {
  padding: 1rem;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.insight-block h3 {
  margin: 0 0 0.5rem;
  color: #374151;
}

ul {
  margin: 0;
  padding-left: 1.25rem;
}

li {
  margin-bottom: 0.4rem;
}
</style>
