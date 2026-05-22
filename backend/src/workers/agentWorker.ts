import { Worker } from "bullmq";
import { redis } from "../lib/redis";
import { prisma } from "../lib/prisma";
import axios from "axios";

const AGENTS_URL = process.env.NEXT_PUBLIC_AGENTS_URL ?? "http://localhost:8000";

export function startAgentWorker() {
  const worker = new Worker(
    "agent-pipeline",
    async (job) => {
      const { runId, brandId, userId, mode, daysAhead } = job.data;

      console.log(`[Worker] Starting agent run ${runId} for brand ${brandId}`);

      // Update run status to running
      await prisma.agentRun.update({
        where: { id: runId },
        data: { status: "running" },
      });

      try {
        // Call Python agents service
        const response = await axios.post(
          `${AGENTS_URL}/runs`,
          { runId, brandId, userId, mode, daysAhead },
          { timeout: 600_000 } // 10 min timeout
        );

        const result = response.data;

        // Save outputs
        await prisma.agentRun.update({
          where: { id: runId },
          data: {
            status: "completed",
            completedAt: new Date(),
            pptUrl: result.pptUrl,
            excelUrl: result.excelUrl,
            postsGenerated: result.postsGenerated ?? 0,
            strategyJson: result.strategyJson,
            analystReport: result.analystReport,
            agentStatuses: result.agentStatuses ?? {},
          },
        });

        // Save posts
        if (result.posts?.length) {
          await prisma.post.createMany({
            data: result.posts.map((p: {
              date: string;
              contentType: string;
              topic: string;
              caption?: string;
              hashtags?: string[];
            }) => ({
              agentRunId: runId,
              date: new Date(p.date),
              contentType: p.contentType,
              topic: p.topic,
              caption: p.caption,
              hashtags: p.hashtags ?? [],
            })),
          });
        }

        // Save design assets
        if (result.designAssets?.length) {
          await prisma.designAsset.createMany({
            data: result.designAssets.map((a: {
              imageUrl: string;
              contentType: string;
              topic?: string;
              prompt?: string;
              date?: string;
            }) => ({
              agentRunId: runId,
              imageUrl: a.imageUrl,
              contentType: a.contentType,
              topic: a.topic,
              prompt: a.prompt,
              date: a.date ? new Date(a.date) : null,
            })),
          });
        }

        // Save analytics report
        if (result.analystReport) {
          const r = result.analystReport;
          await prisma.analyticsReport.create({
            data: {
              brandId,
              followerCount: r.followerCount,
              avgReach: r.avgReach,
              avgEngagementRate: r.avgEngagementRate,
              postsAnalyzed: r.postsAnalyzed,
              topPosts: r.topPosts,
              rawReport: r,
            },
          });
        }

        console.log(`[Worker] Run ${runId} completed`);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        console.error(`[Worker] Run ${runId} failed:`, message);

        await prisma.agentRun.update({
          where: { id: runId },
          data: {
            status: "failed",
            completedAt: new Date(),
            errorMessage: message,
          },
        });

        throw err; // BullMQ will retry
      }
    },
    {
      connection: redis,
      concurrency: 2,
    }
  );

  worker.on("failed", (job, err) => {
    console.error(`[Worker] Job ${job?.id} failed permanently:`, err.message);
  });

  console.log("[Worker] Agent pipeline worker started");
  return worker;
}
