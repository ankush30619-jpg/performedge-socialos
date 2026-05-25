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

    // Always execute directly in background (no BullMQ for pipeline runs)
    // setImmediate ensures the 202 response is sent before heavy work starts
    setImmediate(() => {
      executePipelineRun(run.id, body.brandId, user.id, body.mode, body.daysAhead).catch(
        (e) => console.error("[Pipeline] Background run error:", e)
      );
    });
    console.log(`[Pipeline] Run ${run.id} started (direct execution)`);

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

    // Set SSE headers — use request origin for CORS compatibility with EventSource
    const origin = req.headers.origin || "*";
    reply.raw.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Credentials": "true",
    });

    const keepAlive = setInterval(() => {
      reply.raw.write(": keepalive\n\n");
    }, 15000);

    // Retry connecting to agents SSE — handles race conditions where:
    // 1. Pipeline hasn't registered the run yet (404)
    // 2. Agents service is temporarily unavailable (network error)
    // Retry for up to 90 seconds (90 attempts × 1 second).
    let agentStream = null;
    for (let attempt = 0; attempt < 90; attempt++) {
      try {
        agentStream = await axios.get(`${AGENTS_URL}/runs/${runId}/stream`, {
          responseType: "stream",
          timeout: 600_000,
        });
        break; // connected successfully
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response?.status;
        // Retry on 404 (run not started yet) OR on network errors (!status = ECONNREFUSED/timeout)
        if (attempt < 89) {
          await new Promise((r) => setTimeout(r, 1000));
          continue;
        }
        // Exhausted all retries
        clearInterval(keepAlive);
        reply.raw.write(
          `data: ${JSON.stringify({ type: "pipeline_failed", message: `Pipeline could not start after ${attempt + 1}s — HTTP ${status ?? "network error"}` })}\n\n`
        );
        reply.raw.end();
        return;
      }
    }

    if (!agentStream) {
      clearInterval(keepAlive);
      reply.raw.write(
        `data: ${JSON.stringify({ type: "pipeline_failed", message: "Run not started within 90 seconds" })}\n\n`
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
