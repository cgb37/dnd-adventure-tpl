---
layout: default
title: "AI Chatbot"
permalink: /tools/chat/
---

<div class="container py-4">
  <h1 class="mb-3">AI Chatbot</h1>

  <p class="text-body-secondary">
    Dev UI for generating campaign drafts via the local LLM API.
  </p>

  <div class="row g-3">
    <div class="col-12 col-lg-4">
      <div class="card">
        <div class="card-body">
          <div class="mb-3">
            <label for="llmProvider" class="form-label">LLM provider</label>
            <select id="llmProvider" class="form-select"></select>
            <div class="form-text">
              Provider list comes from the API and is saved until you change it.
            </div>
          </div>

          <div class="mb-3">
            <div class="form-text mb-1">Commands</div>
            <ul class="mb-0">
              <li><code>/generate npc</code></li>
              <li><code>/generate monster</code></li>
              <li><code>/generate encounter</code></li>
              <li><code>/generate chapter</code></li>
              <li><code>/generate location</code></li>
            </ul>
          </div>

          <div id="schemaPanel" class="mb-3"></div>
        </div>
      </div>
    </div>

    <div class="col-12 col-lg-8">
      <div class="card">
        <div class="card-body">
          <div class="mb-3">
            <label for="chatInput" class="form-label">Prompt</label>
            <input id="chatInput" class="form-control" type="text" placeholder='Try: /generate npc' />
          </div>

          <div class="d-flex gap-2">
            <button id="sendBtn" class="btn btn-primary" type="button">Send</button>
            <button id="clearBtn" class="btn btn-outline-secondary" type="button">Clear</button>
          </div>

          <pre id="output" class="mt-3 mb-0" style="white-space: pre-wrap;"></pre>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
  window.LLM_API_BASE_URL = "{{ site.llm_api_base_url | default: 'http://localhost:8000' }}";
</script>
<script src="/assets/js/llm-chatbot.js"></script>
