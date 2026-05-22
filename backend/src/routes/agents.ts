import type { FastifyInstance } from "fastify";
import { prisma } from "../lib/prisma";
import { agentQueue } from "../lib/queues";
import axios from "axios";
import { z } from "zod";

const AGENTS_URL = process.env.NEXT_PUBLIC_AGENTS_URL ?? "http://localhost:8000";

const runSchema = z.object({
  brandId: z.string(),
  mode: z.enum(["full", "analyst_only", "strategy_only", "design_only"]).default("full"),
  daysAhead: z.number().int().min(7).max(30).default(15),
});

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

    // Enqueue job — the worker will call the Python agents service
    await agentQueue.add(
      "run-pipeline",
      { runId: run.id, brandId: body.brandId, userId: user.id, mode: body.mode, daysAhead: body.daysAhead },
      { jobId: run.id }
    );

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
    const job = await agentQueue.getJob(runId);
    if (job) await job.remove();

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
    });

    const keepAlive = setInterval(() => {
      reply.raw.write(": keepalive\n\n");
    }, 15000);

    // Proxy SSE from Python agents service
    try {
      const response = await axios.get(`${AGENTS_URL}/runs/${runId}/stream`, {
        responseType: "stream",
      });

      response.data.on("data", (chunk: Buffer) => {
        reply.raw.write(chunk);
      });

      response.data.on("end", () => {
        clearInterval(keepAlive);
        reply.raw.end();
      });

      response.data.on("error", () => {
        clearInterval(keepAlive);
        reply.raw.end();
      });
    } catch {
      clearInterval(keepAlive);
      reply.raw.write(`data: ${JSON.stringify({ type: "error", message: "Agents service unavailable" })}\n\n`);
      reply.raw.end();
    }

    req.raw.on("close", () => {
      clearInterval(keepAlive);
    });
  });
}
