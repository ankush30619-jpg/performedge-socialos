# n8n Integration Blueprint — SocialOS × n8n

## Quick answers (the 5 questions from the project spec)

**1. Will n8n work with the current Claude/Python agents?**
Yes. n8n sits at the trigger + notification layer **above** the existing
LangGraph pipeline. The Python agents continue running unchanged; n8n calls
them via a webhook (`POST /api/runs/n8n-trigger`). See [Architecture](#architecture)
and [Step 1](#step-1-expose-a-webhook-endpoint-in-your-backend).

**2. What does n8n add vs pure code?**
Visual workflow editing, schedules a non-engineer can change, 400+ pre-built
integrations (Slack, Notion, Airtable, Gmail, etc.), and node-by-node error
UI without redeploying code. See the comparison table below.

**3. Which workflows belong in n8n, which stay in code?**
n8n: cron-driven runs, third-party notifications, Instagram webhook ingest,
human approval flows. Code (LangGraph): the agent DAG, prompt orchestration,
quality gating, brand-context loading, SSE streaming. See
[Specific Workflows Better in n8n vs Code](#specific-workflows-better-in-n8n-vs-code).

**4. How do I integrate it step by step?**
(a) Deploy n8n self-hosted on Railway as a second service.
(b) Add `POST /api/runs/n8n-trigger` to the Fastify backend (snippet in
[Step 1](#step-1-expose-a-webhook-endpoint-in-your-backend)).
(c) Have `agents/main.py` POST the callback URL on `pipeline_complete`
(snippet in [Step 2](#step-2-add-completion-webhook-call-in-agentsmainpy)).
(d) Build the starter workflow: cron → trigger → Slack notify on completion
(see [Recommended Start Point](#recommended-start-point)).

**5. Limitations to know about?**
Free-plan execution cap (~5 min) doesn't fit a full pipeline run; no native
SSE consumer (n8n polls instead of streaming); adds a second deployable to
maintain. See [Limitations](#limitations).

---

## n8n vs Pure Code: Honest Comparison

| Aspect | n8n | Current Code (LangGraph) |
|--------|-----|--------------------------|
| **Visual workflow** | ✅ Drag-drop editor | ❌ Code only |
| **Non-dev team usage** | ✅ Anyone can modify | ❌ Developer required |
| **Scheduling (cron)** | ✅ Built-in | 🔶 Manual (Railway cron) |
| **300+ integrations** | ✅ Slack, Notion, Airtable, Gmail... | ❌ Code each one |
| **Error visibility** | ✅ Visual node-by-node | 🔶 Log files |
| **AI agent logic** | 🔶 Limited (basic) | ✅ Full LangGraph power |
| **Custom Python code** | 🔶 Possible but awkward | ✅ Native |
| **Cost** | 💰 $24/mo cloud or self-host | Free (Railway included) |
| **Real-time SSE** | ❌ Not built-in | ✅ Already working |
| **State management** | 🔶 Basic | ✅ Full LangGraph |

## Verdict: Hybrid Architecture (Best of Both)

Don't replace LangGraph with n8n — use n8n as a **trigger + notification layer**
on top of your existing agents. n8n handles: scheduling, external triggers,
notifications, and simple data routing. Your Python agents handle: actual AI work.

## Architecture

```
[TRIGGERS]                    [YOUR SYSTEM]
Instagram webhook    ─────┐
Scheduled cron       ─────┤──► n8n Workflow ──► POST /api/runs ──► LangGraph Pipeline
Manual button        ─────┘                        │                      │
                                                    │                      ▼
[OUTPUTS]                                          ▼              Python Agents
Slack notification  ◄─────── n8n Workflow ◄── Webhook callback     (unchanged)
Notion database     ◄─────── n8n Workflow
Email report        ◄─────── n8n Workflow
Airtable log        ◄─────── n8n Workflow
```

## Step-by-Step Integration

### Step 1: Expose a webhook endpoint in your backend

Add to `backend/src/routes/agents.ts`:

```typescript
// POST /api/runs/n8n-trigger — n8n calls this to start a pipeline run
fastify.post('/api/runs/n8n-trigger', {
  schema: {
    body: {
      type: 'object',
      required: ['brandId', 'mode'],
      properties: {
        brandId:    { type: 'string' },
        mode:       { type: 'string', enum: ['full', 'growth_planner_only'] },
        daysAhead:  { type: 'number', default: 15 },
        n8nRunId:   { type: 'string' },  // for callback tracking
        callbackUrl:{ type: 'string' },  // n8n webhook to call when done
      }
    }
  },
  handler: async (request, reply) => {
    const { brandId, mode, daysAhead, callbackUrl } = request.body as any;
    // ... queue the pipeline run as normal
    // Store callbackUrl in the run record
    // When done, POST result to callbackUrl
    return { runId: '...', status: 'queued' };
  }
});
```

### Step 2: Add completion webhook call in agents/main.py

```python
# In the pipeline_complete handler, after saving to DB:
callback_url = run_config.get("callback_url")
if callback_url:
    async with httpx.AsyncClient() as client:
        await client.post(callback_url, json={
            "runId":          run_id,
            "status":         "completed",
            "postsGenerated": final.get("posts_generated", 0),
            "pptUrl":         final.get("ppt_url"),
            "excelUrl":       final.get("excel_url"),
            "brandName":      brand.get("name"),
        }, timeout=10.0)
```

### Step 3: n8n Workflow 1 — Scheduled Daily Report

```json
{
  "name": "SocialOS Daily Growth Report",
  "nodes": [
    {
      "name": "Every Day 9am",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": { "interval": [{ "field": "hours", "hoursInterval": 24, "triggerAtHour": 9 }] }
      }
    },
    {
      "name": "Get Active Brands",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "https://your-api.railway.app/api/brands",
        "authentication": "genericCredentialType",
        "method": "GET"
      }
    },
    {
      "name": "For Each Brand",
      "type": "n8n-nodes-base.splitInBatches",
      "parameters": { "batchSize": 1 }
    },
    {
      "name": "Trigger Pipeline",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "https://your-api.railway.app/api/runs/n8n-trigger",
        "method": "POST",
        "body": {
          "brandId":     "={{ $json.id }}",
          "mode":        "growth_planner_only",
          "daysAhead":   30,
          "callbackUrl": "={{ $env.N8N_WEBHOOK_URL }}/socialos-complete"
        }
      }
    },
    {
      "name": "Wait for Completion",
      "type": "n8n-nodes-base.wait",
      "parameters": { "resume": "webhook", "path": "socialos-complete" }
    },
    {
      "name": "Send Slack Notification",
      "type": "n8n-nodes-base.slack",
      "parameters": {
        "channel": "#growth-reports",
        "text": "✅ Growth report ready for {{ $json.brandName }} — {{ $json.postsGenerated }} posts generated. Download: {{ $json.pptUrl }}"
      }
    }
  ]
}
```

### Step 4: n8n Workflow 2 — Instagram Mention Trigger

```
Instagram Webhook → n8n → Extract @mention + sentiment
                        → If positive: add to UGC pool in Airtable
                        → If negative: alert Slack for response
                        → Trigger brand-specific response script from SocialOS
```

### Step 5: n8n Workflow 3 — Content Approval Pipeline

```
SocialOS generates posts
  → n8n receives webhook
  → Creates Notion page with all post drafts
  → Sends Slack message "Posts ready for review"
  → Waits for team approval in Slack
  → On approval: triggers scheduling via SocialOS API
  → On rejection: re-triggers with feedback
```

## Specific Workflows Better in n8n vs Code

| Better in n8n | Better in LangGraph code |
|---------------|--------------------------|
| Scheduling (daily/weekly triggers) | AI agent logic (GPT calls, strategy) |
| Slack/email/Notion notifications | Real-time SSE streaming |
| Multi-brand batch processing | Complex state management |
| External API webhooks (Instagram, etc.) | Python data processing |
| Team approval flows | Image generation pipeline |
| CRM data sync (Hubspot, Airtable) | Quality control loops |

## Limitations

1. n8n cloud has execution time limits (5 min on free) — your growth planner takes 3-5 min, so needs paid plan or self-hosting
2. n8n can't handle SSE (server-sent events) natively — your real-time UI stays in code
3. Complex Python logic (pptx generation, Tavily scraping) stays in agents service
4. n8n adds another service to maintain and monitor

## Recommended Start Point

Start with just ONE workflow: **"Slack notification when growth report completes"**
This gives you real n8n value with minimal integration risk:
1. Install n8n (n8n.io/cloud or `docker run -it --rm n8n`)
2. Create 2-step workflow: Webhook trigger → Slack message
3. Update agents/main.py to POST to that webhook on pipeline_complete
4. Test with one brand

Then expand from there.
