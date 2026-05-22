import { Queue, Worker, QueueEvents } from "bullmq";
import { redis } from "./redis";

// ── Agent pipeline queue ──────────────────────────────────────────────────────
export const agentQueue = new Queue("agent-pipeline", {
  connection: redis,
  defaultJobOptions: {
    attempts: 2,
    backoff: { type: "exponential", delay: 5000 },
    removeOnComplete: 100,
    removeOnFail: 50,
  },
});

export const agentQueueEvents = new QueueEvents("agent-pipeline", {
  connection: redis,
});

// ── Instagram scheduled-post queue ───────────────────────────────────────────
export const scheduleQueue = new Queue("instagram-schedule", {
  connection: redis,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: "exponential", delay: 10000 },
    removeOnComplete: 200,
    removeOnFail: 100,
  },
});

// ── Self-learning (15-day cron) queue ─────────────────────────────────────────
export const learningQueue = new Queue("brand-learning", {
  connection: redis,
  defaultJobOptions: {
    attempts: 3,
    removeOnComplete: 20,
    removeOnFail: 20,
  },
});

// Schedule the 15-day cron on startup
export async function scheduleLearningCron() {
  const existing = await learningQueue.getJobSchedulers();
  if (!existing.some((s) => s.name === "15d-relearn")) {
    await learningQueue.upsertJobScheduler(
      "15d-relearn",
      { pattern: "0 3 */15 * *" }, // 3am every 15 days
      {
        name: "brand-relearn",
        data: { trigger: "cron_15d" },
      }
    );
    console.log("[Queue] 15-day learning cron scheduled");
  }
}
