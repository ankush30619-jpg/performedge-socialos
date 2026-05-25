import type { FastifyInstance } from "fastify";
import { prisma } from "../lib/prisma";
import axios from "axios";
import { z } from "zod";

const AGENTS_URL = process.env.NEXT_PUBLIC_AGENTS_URL ?? "http://localhost:8000";

const runSchema = z.object({
  brandId: z.string(),
  mode: z.enum(["full", "analyst_only", "strategy_only", "design_only", "growth_planner_only"]).default("full"),
  daysAhead: z.number().int().min(1).max(30).default(15),
});

// ── Shared: execute pipeline + save results ─────────────────────────────────
async function executePipelineRun(runId: string, brandId: string, userId: string, mode: string, daysAhead: number) {
  console.log(`[Pipeline] Starting run ${runId} for brand ${brandId}`);

  await prisma.agentRun.update({
    where: { id: runId },
    data: { status: "running" },
  });

  try {
    const response = await axios.post(
      `${AGENTS_URL}/runs`,
      { runId, brandId, userId, mode, daysAhead },
      { timeout: 600_000 }
    );

    const result = response.data;

    // Save run outputs
    await prisma.agentRun.update({
      where: { id: runId },
      data: {
        status: "completed",
        completedAt: new Date(),
        pptUrl: result.pptUrl ?? null,
        excelUrl: result.excelUrl ?? null,
        postsGenerated: result.postsGenerated ?? 0,
        strategyJson: result.strategyJson ?? null,
        analystReport: result.analystReport ?? null,
        agentStatuses: result.agentStatuses ?? {},
      },
    });

    // Save posts
    if (result.posts?.length) {
      await prisma.post.createMany({
        data: result.posts.map((p: {
          date: string; contentType: string; topic: string;
          caption?: string; hashtags?: string[];
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
          imageUrl: string; contentType: string;
          topic?: string; prompt?: string; date?: string;
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
    if (result.analystReport && Object.keys(result.analystReport).length > 0) {
      const r = result.analystReport;
      try {
        await prisma.analyticsReport.create({
          data: {
            brandId,
            followerCount: r.followerCount ?? 0,
            avgReach: r.avgReach ?? 0,
            avgEngagementRate: r.avgEngagementRate ?? 0,
            postsAnalyzed: r.postsAnalyzed ?? 0,
            topPosts: r.topPosts ?? [],
            rawReport: r,
          },
        });
      } catch {
        // analytics report creation is non-fatal
      }
    }

    console.log(`[Pipeline] Run ${runId} completed — ${result.postsGenerated ?? 0} posts`);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error(`[Pipeline] Run ${runId} failed:`, message);

    await prisma.agentRun.update({
      where: { id: runId },
      data: {
        status: "failed",
        completedAt: new Date(),
        errorMessage: message,
      },
    });
  }
}

export async function agentRoutes(app: FastifyInstance) {
  const auth = { preHandler: [app.authenticate] };

  // POST /api/agents/run — start a new pipeline run
  app.post("/api/agents/run", auth, async (req, reply) => {
    const user = req.user as { id: string };
    const body = runSchema.parse(req.body);

    // Verify brand ownership
    const brand = await prisma.brand.findFirst({
      where: { id: body.brandId, userId: user.id },
    });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });

    // Create run record in DB
    const run = await prisma.agentRun.create({
      data: {
        brandId: body.brandId,
        userId: user.id,
        mode: body.mode,
        daysAhead: body.daysAhead,
        status: "pending",
        startedAt: new Date(),
      },
    });

    // Try BullMQ first; fall back to direct async execution
    let queued = false;
    try {
      const { agentQueue } = await import("../lib/queues");
      await agentQueue.add(
        "run-pipeline",
        { runId: run.id, brandId: body.brandId, userId: user.id, mode: body.mode, daysAhead: body.daysAhead },
        { jobId: run.id, attempts: 1 }
      );
      queued = true;
      console.log(`[Pipeline] Run ${run.id} queued via BullMQ`);
    } catch {
      // Redis unavailable — run directly in background
    }

    if (!queued) {
      // Kick off directly as a background async task (no await)
      setImmediate(() => {
        executePipelineRun(run.id, body.brandId, user.id, body.mode, body.daysAhead).catch(
          (e) => console.error("[Pipeline] Background run error:", e)
        );
      });
      console.log(`[Pipeline] Run ${run.id} started directly (no Redis)`);
    }

    return reply.code(202).send({ run });
  });

  // GET /api/agents/runs/:runId — poll run status
  app.get("/api/agents/runs/:runId", auth, async (req, reply) => {
    const user = req.user as { id: string };
    const { runId } = req.params as { runId: string };

    const run = await prisma.agentRun.findFirst({
      where: { id: runId, userId: user.id },
      include: { posts: true, designAssets: true },
    });
    if (!run) return reply.code(404).send({ message: "Run not found" });

    return reply.send({ run });
  });

  // GET /api/agents/runs?brandId=xxx — list runs for a brand
  app.get("/api/agents/runs", auth, async (req, reply) => {
    const user = req.user as { id: string };
    const { brandId } = req.query as { brandId?: string };

    const runs = await prisma.agentRun.findMany({
      where: {
        userId: user.id,
        ...(brandId ? { brandId } : {}),
      },
      orderBy: { createdAt: "desc" },
      take: 20,
      include: {
        posts: { take: 5 },
        designAssets: { take: 4 },
      },
    });

    return reply.send({ runs });
  });

  // POST /api/agents/runs/:runId/stop
  app.post("/api/agents/runs/:runId/stop", auth, async (req, reply) => {
    const user = req.user as { id: string };
    const { runId } = req.params as { runId: string };

    const run = await prisma.agentRun.findFirst({ where: { id: runId, userId: user.id } });
    if (!run) return reply.code(404).send({ message: "Run not found" });

    // Try to remove from queue if still pending
    try {
      const { agentQueue } = await import("../lib/queues");
      const job = await agentQueue.getJob(runId);
      if (job) await job.remove();
    } catch {
      // Redis unavailable — skip queue cleanup
    }

    // Update status
    await prisma.agentRun.update({
      where: { id: runId },
      data: { status: "stopped", completedAt: new Date() },
    });

    // Notify Python agents service to stop if running
    try {
      await axios.post(`${AGENTS_URL}/runs/${runId}/stop`);
    } catch {
      // ignore if agents service not reachable
    }

    return reply.send({ message: "Run stopped" });
  });

  // GET /api/agents/runs/:runId/stream — SSE proxy from Python agents
  app.get("/api/agents/runs/:runId/stream", auth, async (req, reply) => {
    const { runId } = req.params as { runId: string };

    // Set SSE headers
    reply.raw.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
      "Access-Control-Allow-Origin": "*",
    });

    const keepAlive = setInterval(() => {
      reply.raw.write(": keepalive\n\n");
    }, 15000);

    // Retry connecting to agents SSE — handles race condition where
    // the pipeline hasn't registered the run yet when frontend connects.
    // Retry for up to 60 seconds (60 attempts × 1 second).
    let agentStream = null;
    for (let attempt = 0; attempt < 60; attempt++) {
      try {
        agentStream = await axios.get(`${AGENTS_URL}/runs/${runId}/stream`, {
          responseType: "stream",
          timeout: 600_000,
        });
        break; // connected successfully
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response?.status;
        if (status === 404 && attempt < 59) {
          // Run not started yet — wait 1 second and retry
          await new Promise((r) => setTimeout(r, 1000));
          continue;
        }
        // Fatal error or exhausted retries
        clearInterval(keepAlive);
        reply.raw.write(
          `data: ${JSON.stringify({ type: "pipeline_failed", message: "Pipeline could not start — check server logs" })}\n\n`
        );
        reply.raw.end();
        return;
      }
    }

    if (!agentStream) {
      clearInterval(keepAlive);
      reply.raw.write(
        `data: ${JSON.stringify({ type: "pipeline_failed", message: "Run not started within 60 seconds" })}\n\n`
      );
      reply.raw.end();
      return;
    }

    agentStream.data.on("data", (chunk: Buffer) => {
      reply.raw.write(chunk);
    });

    agentStream.data.on("end", () => {
      clearInterval(keepAlive);
      reply.raw.end();
    });

    agentStream.data.on("error", () => {
      clearInterval(keepAlive);
      reply.raw.end();
    });

    req.raw.on("close", () => {
      clearInterval(keepAlive);
    });
  });
}
