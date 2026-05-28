import type { FastifyInstance } from "fastify";
import { prisma } from "../lib/prisma";
import axios from "axios";
import { z } from "zod";
import crypto from "crypto";

// ── Token decryption (same algorithm as learningWorker.ts / meta.ts) ──────────
function decryptToken(encrypted: string): string {
  const key = Buffer.from(process.env.ENCRYPTION_KEY ?? "", "base64");
  const buf = Buffer.from(encrypted, "base64");
  const iv     = buf.subarray(0, 12);
  const tag    = buf.subarray(12, 28);
  const cipher = buf.subarray(28);
  const dec = crypto.createDecipheriv("aes-256-gcm", key, iv);
  dec.setAuthTag(tag);
  return Buffer.concat([dec.update(cipher), dec.final()]).toString("utf8");
}

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
    // Fetch full brand from Prisma directly — NOT the sanitized API endpoint which strips igAccessToken
    const brand = await prisma.brand.findUnique({ where: { id: brandId } });

    // Decrypt IG token server-side — only travels over internal Railway network to agents
    let igAccessToken: string | null = null;
    if (brand?.igAccessToken) {
      try { igAccessToken = decryptToken(brand.igAccessToken); }
      catch { console.warn(`[Pipeline] Could not decrypt token for brand ${brandId}`); }
    }

    const response = await axios.post(
      `${AGENTS_URL}/runs`,
      {
        runId, brandId, userId, mode, daysAhead,
        brand: brand ? {
          id:                brand.id,
          name:              brand.name,
          niche:             brand.niche,
          industry:          (brand as any).industry          ?? "",
          website:           brand.website                    ?? "",
          language:          (brand as any).language          ?? "English",
          positioning:       (brand as any).positioning       ?? "",
          differentiation:   (brand as any).differentiation   ?? "",
          brandStory:        (brand as any).brandStory        ?? "",
          credentials:       (brand as any).credentials       ?? "",
          targetAudience:    brand.targetAudience             ?? "",
          audienceAge:       (brand as any).audienceAge       ?? "",
          audienceProfession:(brand as any).audienceProfession ?? "",
          audiencePainPoints:(brand as any).audiencePainPoints ?? "",
          audienceLevel:     (brand as any).audienceLevel     ?? "",
          audienceLanguage:  (brand as any).audienceLanguage  ?? "",
          audienceAspirations:(brand as any).audienceAspirations ?? "",
          tone:              brand.tone                       ?? "Professional",
          voiceStyle:        (brand as any).voiceStyle        ?? "",
          catchphrases:      (brand as any).catchphrases      ?? "",
          forbiddenWords:    (brand as any).forbiddenWords    ?? "",
          usesSlang:         (brand as any).usesSlang         ?? false,
          hookStyle:         (brand as any).hookStyle         ?? "",
          ctaStyle:          (brand as any).ctaStyle          ?? "",
          hookFormulas:      (brand as any).hookFormulas      ?? "",
          bestHooks:         (brand as any).bestHooks         ?? "",
          worstContent:      (brand as any).worstContent      ?? "",
          contentPillars:    (brand as any).contentPillars    ?? [],
          competitors:       (brand as any).competitors       ?? [],
          idealVideoLength:  (brand as any).idealVideoLength  ?? "",
          instagramUrl:      (brand as any).instagramUrl      ?? "",
          logoUrl:           (brand as any).logoUrl           ?? "",
          igAccountId:       brand.igAccountId,
          igAccessToken,     // decrypted — internal network only, never sent to frontend
          igUsername:        brand.igUsername,
          igFollowers:       brand.igFollowers,
          knowledgeJson:     brand.knowledgeJson,
        } : null,
      },
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

    // Save posts (with full copywriter brief in briefJson)
    if (result.posts?.length) {
      await prisma.post.createMany({
        data: result.posts.map((p: Record<string, any>) => ({
          agentRunId: runId,
          date: new Date(p.date),
          contentType: p.contentType,
          topic: p.topic,
          caption: p.caption,
          hashtags: p.hashtags ?? [],
          briefJson: {
            hook:              p.hook              ?? null,
            hook_variations:   p.hook_variations   ?? [],
            caption_short:     p.caption_short     ?? null,
            caption_long:      p.caption_long      ?? null,
            cta:               p.cta               ?? null,
            seo_keywords:      p.seo_keywords      ?? [],
            audio_suggestion:  p.audio_suggestion  ?? null,
            carousel_slides:   p.carousel_slides   ?? null,
            story_sequence:    p.story_sequence    ?? null,
            graphic_layout:    p.graphic_layout    ?? null,
            reel_script:       p.reel_script       ?? null,
            posting_time:      p.posting_time      ?? null,
            visual_brief:      p.visual_brief      ?? null,
            emotional_trigger: p.emotional_trigger ?? null,
            conversion_angle:  p.conversion_angle  ?? null,
          },
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
  // Visibility scoped by brand ownership (not run owner), so a run created by
  // any user shows to everyone who can see the brand.
  app.get("/api/agents/runs/:runId", auth, async (req, reply) => {
    const user = req.user as { id: string; bypass?: boolean };
    const { runId } = req.params as { runId: string };

    const run = await prisma.agentRun.findUnique({
      where: { id: runId },
      include: { posts: true, designAssets: true, brand: { select: { userId: true } } },
    });
    if (!run) return reply.code(404).send({ message: "Run not found" });
    if (!user.bypass && run.brand.userId !== user.id) {
      return reply.code(404).send({ message: "Run not found" });
    }

    return reply.send({ run });
  });

  // GET /api/agents/runs?brandId=xxx — list runs for a brand
  // Scoped by brand (not user) so all team members see the same history
  // when working on a shared brand. Visibility = brand ownership, not run-owner.
  app.get("/api/agents/runs", auth, async (req, reply) => {
    const user = req.user as { id: string; bypass?: boolean };
    const { brandId } = req.query as { brandId?: string };

    // If a brandId is given, verify the user can see this brand, then return ALL runs for it.
    // If no brandId, fall back to user's own runs (legacy behaviour for dashboard widgets).
    let whereClause: { brandId?: string; userId?: string };
    if (brandId) {
      const brand = await prisma.brand.findFirst({
        where: user.bypass ? { id: brandId } : { id: brandId, userId: user.id },
      });
      if (!brand) return reply.code(404).send({ message: "Brand not found" });
      whereClause = { brandId };
    } else {
      whereClause = { userId: user.id };
    }

    const runs = await prisma.agentRun.findMany({
      where: whereClause,
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
