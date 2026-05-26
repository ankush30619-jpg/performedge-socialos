import "dotenv/config";
import Fastify, { FastifyRequest, FastifyReply } from "fastify";
import { prisma } from "./lib/prisma";
import cors from "@fastify/cors";
import helmet from "@fastify/helmet";
import jwt from "@fastify/jwt";
import rateLimit from "@fastify/rate-limit";
import multipart from "@fastify/multipart";

import { authRoutes } from "./routes/auth";
import { brandRoutes } from "./routes/brands";
import { agentRoutes } from "./routes/agents";
import { analyticsRoutes } from "./routes/analytics";
import { metaRoutes } from "./routes/meta";
import { instagramRoutes } from "./routes/instagram";

const PORT = parseInt(process.env.PORT ?? "4000");
const HOST = process.env.HOST ?? "0.0.0.0";

// ── Bypass user (set at startup, reused in authenticate decorator) ────────────
// Uses the FIRST real user in DB so existing brands/data are all accessible.
let _bypassUserId  = "";
let _bypassEmail   = "";
let _bypassRole    = "admin";

async function ensureBypassUser() {
  try {
    // First priority: find the user who actually HAS brands in the DB
    // This ensures existing brand data is always visible after a redeploy
    const brandWithUser = await prisma.brand.findFirst({
      select: { userId: true },
      orderBy: { createdAt: "asc" },
    });
    if (brandWithUser?.userId) {
      const owner = await prisma.user.findUnique({ where: { id: brandWithUser.userId } });
      if (owner) {
        _bypassUserId = owner.id;
        _bypassEmail  = owner.email;
        _bypassRole   = owner.role ?? "admin";
        console.log(`   Bypass auth        →  using brand owner ${owner.email} (${owner.id})`);
        return;
      }
    }

    // Second priority: first real non-dev user
    const existing = await prisma.user.findFirst({
      where: { NOT: { email: "dev@socialos.local" } },
      orderBy: { createdAt: "asc" },
    });
    if (existing) {
      _bypassUserId = existing.id;
      _bypassEmail  = existing.email;
      _bypassRole   = existing.role ?? "admin";
      console.log(`   Bypass auth        →  using first real user ${existing.email} (${existing.id})`);
      return;
    }

    // Fallback: create a dev placeholder if no user exists yet
    const u = await prisma.user.upsert({
      where:  { email: "dev@socialos.local" },
      update: {},
      create: { email: "dev@socialos.local", passwordHash: "dev-bypass-no-pw", name: "Dev User", role: "admin" },
    });
    _bypassUserId = u.id;
    _bypassEmail  = u.email;
    console.log(`   Bypass auth        →  created dev placeholder (${u.id})`);
  } catch (e) {
    console.warn("   Bypass auth        →  ⚠️  could not set up bypass user:", (e as Error).message);
  }
}

async function main() {
  const app = Fastify({
    logger: false, // use console.log for cleaner dev output
  });

  // ── Plugins ─────────────────────────────────────────────────────────────────
  await app.register(helmet, { contentSecurityPolicy: false });

  await app.register(cors, {
    origin: (origin, cb) => {
      const allowed = [
        "http://localhost:3000",
        "http://localhost:4000",
        process.env.NEXTAUTH_URL ?? "http://localhost:3000",
        process.env.FRONTEND_URL ?? "http://localhost:3000",
      ].filter(Boolean);
      // Allow serveo / ngrok tunnels and any https origin
      if (!origin || allowed.includes(origin) || origin.includes("serveousercontent.com") || origin.includes("ngrok.io") || origin.includes("ngrok-free.app")) {
        cb(null, true);
      } else {
        cb(null, true); // allow all in dev — restrict in prod
      }
    },
    credentials: true,
  });

  await app.register(rateLimit, {
    max: 200,
    timeWindow: "1 minute",
  });

  await app.register(jwt, {
    secret: process.env.NEXTAUTH_SECRET!,
  });

  await app.register(multipart, { limits: { fileSize: 50 * 1024 * 1024 } });

  // ── Auth decorator ───────────────────────────────────────────────────────────
  // When BYPASS_AUTH=true (dev mode), skip JWT and inject the dev user.
  // BYPASS_AUTH defaults to true for this internal tool (set BYPASS_AUTH=false to enable login)
  const BYPASS = process.env.BYPASS_AUTH !== "false";

  if (BYPASS) {
    await ensureBypassUser();
  }

  app.decorate(
    "authenticate",
    async function (req: FastifyRequest, reply: FastifyReply) {
      if (BYPASS) {
        (req as FastifyRequest & { user: unknown }).user = {
          id:     _bypassUserId,
          email:  _bypassEmail,
          role:   _bypassRole,
          bypass: true,   // signals routes to skip userId ownership checks
        };
        return;
      }
      try {
        await req.jwtVerify();
      } catch {
        return reply.code(401).send({ message: "Unauthorized" });
      }
    }
  );

  // ── Bypass token endpoint (no auth needed — frontend auto-login) ──────────────
  // Returns a 30-day JWT for the bypass user. Only active when BYPASS is enabled.
  app.get("/api/auth/bypass-token", async (req, reply) => {
    if (!BYPASS || !_bypassUserId) {
      return reply.code(403).send({ message: "Bypass auth not enabled" });
    }
    const token = app.jwt.sign(
      { id: _bypassUserId, email: _bypassEmail, role: _bypassRole },
      { expiresIn: "30d" }
    );
    return reply.send({ token, userId: _bypassUserId, email: _bypassEmail });
  });

  // ── Routes ───────────────────────────────────────────────────────────────────
  await app.register(authRoutes);
  await app.register(brandRoutes);
  await app.register(agentRoutes);
  await app.register(analyticsRoutes);
  await app.register(metaRoutes);
  await app.register(instagramRoutes);

  // ── Health check ─────────────────────────────────────────────────────────────
  app.get("/health", async () => ({
    status: "ok",
    service: "socialos-backend",
    version: "1.0.0",
    ts: new Date().toISOString(),
  }));

  // ── Start HTTP server ────────────────────────────────────────────────────────
  await app.listen({ port: PORT, host: HOST });
  console.log(`\n🚀 SocialOS Backend   →  http://localhost:${PORT}`);
  console.log(`   Health check       →  http://localhost:${PORT}/health\n`);

  // ── Start BullMQ workers AFTER server is up (non-fatal if Redis fails) ───────
  try {
    const { startAgentWorker } = await import("./workers/agentWorker");
    const { startLearningWorker } = await import("./workers/learningWorker");
    const { startScheduleWorker } = await import("./workers/scheduleWorker");
    const { scheduleLearningCron } = await import("./lib/queues");

    startAgentWorker();
    startLearningWorker();
    startScheduleWorker();
    await scheduleLearningCron();
    console.log("   BullMQ workers    →  running");
  } catch (err) {
    console.warn("   BullMQ workers    →  ⚠️  failed to start (Redis issue) — API still works");
    console.warn("   Redis error:", (err as Error).message);
  }
}

main().catch((err) => {
  console.error("Fatal startup error:", err);
  process.exit(1);
});
