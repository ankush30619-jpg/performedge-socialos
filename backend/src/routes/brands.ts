import type { FastifyInstance } from "fastify";
import { prisma } from "../lib/prisma";
import { Prisma } from "@prisma/client";
import { learningQueue } from "../lib/queues";
import { z } from "zod";

const brandSchema = z.object({
  // ── Core Identity ────────────────────────────────────────────────────────
  name:            z.string().min(1),
  niche:           z.string().optional(),
  industry:        z.string().optional(),
  website:         z.string().url().optional().or(z.literal("")),
  instagramUrl:    z.string().optional(),
  language:        z.string().optional(),
  positioning:     z.string().optional(),
  differentiation: z.string().optional(),
  brandStory:      z.string().optional(),
  credentials:     z.string().optional(),

  // ── Brand Identity ───────────────────────────────────────────────────────
  logoUrl:       z.string().optional(),
  guidelinesUrl: z.string().optional(),
  colors:        z.object({
    primary:   z.string(),
    secondary: z.string().optional(),
    accent:    z.string().optional(),
    palette:   z.array(z.string()).optional(),
  }).optional(),
  campaignUrls:   z.array(z.object({ name: z.string(), url: z.string(), type: z.string().optional() })).optional(),
  brandMediaUrls: z.array(z.object({ name: z.string(), url: z.string(), type: z.string().optional() })).optional(),

  // ── Target Audience ──────────────────────────────────────────────────────
  targetAudience:       z.string().optional(),
  audienceAge:          z.string().optional(),
  audienceProfession:   z.string().optional(),
  audiencePainPoints:   z.string().optional(),
  audienceLevel:        z.string().optional(),
  audienceLanguage:     z.string().optional(),
  audienceAspirations:  z.string().optional(),
  audiencePersona:      z.array(z.object({
    name: z.string(), age: z.string().optional(),
    job: z.string().optional(), goals: z.string().optional(), frustrations: z.string().optional(),
  })).optional(),

  // ── Voice & Style ────────────────────────────────────────────────────────
  tone:          z.string().optional(),
  voiceStyle:    z.string().optional(),
  catchphrases:  z.string().optional(),
  forbiddenWords:z.string().optional(),
  usesSlang:     z.boolean().optional(),
  hookStyle:     z.string().optional(),
  ctaStyle:      z.string().optional(),

  // ── Content Strategy ─────────────────────────────────────────────────────
  contentPillars:   z.array(z.string()).optional(),
  idealVideoLength: z.string().optional(),
  hookFormulas:     z.string().optional(),
  bestHooks:        z.string().optional(),
  worstContent:     z.string().optional(),
  competitors:      z.array(z.object({
    name: z.string(), handle: z.string().optional(), notes: z.string().optional(),
  })).optional(),

  // ── IG / AI knowledge ────────────────────────────────────────────────────
  igAccountId:  z.string().optional(),
  igAccessToken:z.string().optional(),
  knowledgeJson:z.record(z.unknown()).optional(),
});

export async function brandRoutes(app: FastifyInstance) {
  const auth = { preHandler: [app.authenticate] };

  // Strip sensitive fields before returning brands to frontend
  function sanitizeBrand(brand: Record<string, unknown>) {
    // Never expose the encrypted access token
    const { igAccessToken, ...safe } = brand;
    return safe;
  }

  // GET /api/brands
  app.get("/api/brands", auth, async (req, reply) => {
    const user = req.user as { id: string; bypass?: boolean };
    // In bypass mode (single-user internal tool) return ALL brands regardless of userId
    const where = user.bypass ? {} : { userId: user.id };
    const brands = await prisma.brand.findMany({
      where,
      orderBy: { createdAt: "desc" },
    });
    return reply.send({ brands: brands.map(b => sanitizeBrand(b as unknown as Record<string, unknown>)) });
  });

  // GET /api/brands/:id
  app.get("/api/brands/:id", auth, async (req, reply) => {
    const user = req.user as { id: string; bypass?: boolean };
    const { id } = req.params as { id: string };
    // In bypass mode allow access to any brand
    const where = user.bypass ? { id } : { id, userId: user.id };
    const brand = await prisma.brand.findFirst({ where });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });
    return reply.send({ brand: sanitizeBrand(brand as unknown as Record<string, unknown>) });
  });

  // POST /api/brands
  app.post("/api/brands", auth, async (req, reply) => {
    const user = req.user as { id: string };
    const data = brandSchema.parse(req.body);
    const brand = await prisma.brand.create({
      data: {
        ...data,
        userId:         user.id,
        website:        data.website || null,
        colors:         data.colors          as Prisma.InputJsonValue ?? Prisma.JsonNull,
        campaignUrls:   data.campaignUrls    as Prisma.InputJsonValue ?? Prisma.JsonNull,
        brandMediaUrls: data.brandMediaUrls  as Prisma.InputJsonValue ?? Prisma.JsonNull,
        audiencePersona:data.audiencePersona as Prisma.InputJsonValue ?? Prisma.JsonNull,
        competitors:    data.competitors     as Prisma.InputJsonValue ?? Prisma.JsonNull,
        contentPillars: data.contentPillars  as Prisma.InputJsonValue ?? Prisma.JsonNull,
        knowledgeJson:  data.knowledgeJson   as Prisma.InputJsonValue ?? Prisma.JsonNull,
      },
    });
    return reply.code(201).send({ brand });
  });

  // PUT /api/brands/:id
  app.put("/api/brands/:id", auth, async (req, reply) => {
    const user = req.user as { id: string; bypass?: boolean };
    const { id } = req.params as { id: string };
    const data = brandSchema.partial().parse(req.body);

    const existing = await prisma.brand.findFirst({ where: user.bypass ? { id } : { id, userId: user.id } });
    if (!existing) return reply.code(404).send({ message: "Brand not found" });

    // Destructure JSON fields out of data so we can cast them separately
    const {
      colors, campaignUrls, brandMediaUrls, audiencePersona,
      competitors, contentPillars, knowledgeJson, ...scalarData
    } = data;

    const brand = await prisma.brand.update({
      where: { id },
      data: {
        ...scalarData,
        ...(colors          !== undefined && { colors:          colors          as Prisma.InputJsonValue }),
        ...(campaignUrls    !== undefined && { campaignUrls:    campaignUrls    as Prisma.InputJsonValue }),
        ...(brandMediaUrls  !== undefined && { brandMediaUrls:  brandMediaUrls  as Prisma.InputJsonValue }),
        ...(audiencePersona !== undefined && { audiencePersona: audiencePersona as Prisma.InputJsonValue }),
        ...(competitors     !== undefined && { competitors:     competitors     as Prisma.InputJsonValue }),
        ...(contentPillars  !== undefined && { contentPillars:  contentPillars  as Prisma.InputJsonValue }),
        ...(knowledgeJson   !== undefined && { knowledgeJson:   knowledgeJson   as Prisma.InputJsonValue }),
      },
    });
    return reply.send({ brand });
  });

  // DELETE /api/brands/:id
  app.delete("/api/brands/:id", auth, async (req, reply) => {
    const user = req.user as { id: string; bypass?: boolean };
    const { id } = req.params as { id: string };
    const existing = await prisma.brand.findFirst({ where: user.bypass ? { id } : { id, userId: user.id } });
    if (!existing) return reply.code(404).send({ message: "Brand not found" });
    await prisma.brand.delete({ where: { id } });
    return reply.code(204).send();
  });

  // POST /api/brands/:id/relearn — trigger self-learning manually
  app.post("/api/brands/:id/relearn", auth, async (req, reply) => {
    const user = req.user as { id: string; bypass?: boolean };
    const { id } = req.params as { id: string };
    const existing = await prisma.brand.findFirst({ where: user.bypass ? { id } : { id, userId: user.id } });
    if (!existing) return reply.code(404).send({ message: "Brand not found" });

    const job = await learningQueue.add("brand-relearn", {
      brandId: id,
      userId: user.id,
      trigger: "manual",
    });

    return reply.send({ message: "Re-learn queued", jobId: job.id });
  });

  // GET /api/brands/:id/learning-logs — last 20 learning events
  app.get("/api/brands/:id/learning-logs", auth, async (req, reply) => {
    const user = req.user as { id: string; bypass?: boolean };
    const { id } = req.params as { id: string };

    const brand = await prisma.brand.findFirst({ where: user.bypass ? { id } : { id, userId: user.id } });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });

    const logs = await prisma.brandLearningLog.findMany({
      where: { brandId: id },
      orderBy: { createdAt: "desc" },
      take: 20,
      select: {
        id:        true,
        trigger:   true,
        summary:   true,
        createdAt: true,
        // rawData omitted — can be large
      },
    });

    return reply.send({ logs });
  });
}
