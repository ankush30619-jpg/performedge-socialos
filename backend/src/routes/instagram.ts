/**
 * Instagram Publishing Routes — Phase 7
 * POST /api/instagram/publish        — publish a post to Instagram immediately
 * POST /api/instagram/schedule       — schedule a post via BullMQ
 * PUT  /api/instagram/posts/:id/status — approve / reject a draft post
 * GET  /api/instagram/posts/:brandId  — list all posts for a brand
 */

import type { FastifyInstance } from "fastify";
import { prisma } from "../lib/prisma";
import { scheduleQueue } from "../lib/queues";
import { z } from "zod";
import crypto from "crypto";

const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY!;
const GRAPH_BASE = "https://graph.facebook.com/v21.0";

// ── Token decrypt ──────────────────────────────────────────────────────────────
function decryptToken(enc: string): string {
  const buf = Buffer.from(enc, "base64");
  const iv = buf.slice(0, 12);
  const tag = buf.slice(12, 28);
  const data = buf.slice(28);
  const keyBuf = Buffer.from(ENCRYPTION_KEY, "base64");
  const decipher = crypto.createDecipheriv("aes-256-gcm", keyBuf, iv);
  decipher.setAuthTag(tag);
  return decipher.update(data) + decipher.final("utf8");
}

// ── Meta Graph API helpers ─────────────────────────────────────────────────────

async function createMediaContainer(
  igAccountId: string,
  accessToken: string,
  imageUrl: string,
  caption: string,
  mediaType: "IMAGE" | "REELS" = "IMAGE"
): Promise<string> {
  const params = new URLSearchParams({
    image_url: imageUrl,
    caption,
    access_token: accessToken,
    media_type: mediaType,
  });

  const res = await fetch(`${GRAPH_BASE}/${igAccountId}/media`, {
    method: "POST",
    body: params,
  });
  const data = (await res.json()) as { id?: string; error?: { message: string } };
  if (!data.id) throw new Error(data.error?.message ?? "Failed to create media container");
  return data.id;
}

async function publishMediaContainer(
  igAccountId: string,
  accessToken: string,
  creationId: string
): Promise<string> {
  const params = new URLSearchParams({
    creation_id: creationId,
    access_token: accessToken,
  });

  const res = await fetch(`${GRAPH_BASE}/${igAccountId}/media_publish`, {
    method: "POST",
    body: params,
  });
  const data = (await res.json()) as { id?: string; error?: { message: string } };
  if (!data.id) throw new Error(data.error?.message ?? "Failed to publish media");
  return data.id;
}

async function waitForContainerReady(
  containerId: string,
  accessToken: string,
  maxAttempts = 10
): Promise<void> {
  for (let i = 0; i < maxAttempts; i++) {
    const res = await fetch(
      `${GRAPH_BASE}/${containerId}?fields=status_code&access_token=${accessToken}`
    );
    const data = (await res.json()) as { status_code?: string };
    if (data.status_code === "FINISHED") return;
    if (data.status_code === "ERROR") throw new Error("Media container processing failed");
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("Media container timed out");
}

// ── Routes ─────────────────────────────────────────────────────────────────────

export async function instagramRoutes(app: FastifyInstance) {
  const auth = { preHandler: [app.authenticate] };

  // ── GET /api/instagram/posts/:brandId — list posts with approval status ──────
  app.get("/api/instagram/posts/:brandId", auth, async (req, reply) => {
    const { brandId } = req.params as { brandId: string };
    const userId = (req.user as { id: string }).id;

    const brand = await prisma.brand.findFirst({ where: { id: brandId, userId } });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });

    // Get latest run's posts
    const latestRun = await prisma.agentRun.findFirst({
      where: { brandId, userId, status: "completed" },
      orderBy: { createdAt: "desc" },
      include: {
        posts: { orderBy: { date: "asc" } },
        designAssets: true,
      },
    });

    return reply.send({
      posts: latestRun?.posts ?? [],
      designAssets: latestRun?.designAssets ?? [],
      runId: latestRun?.id ?? null,
      igConnected: !!brand.igAccountId && !!brand.igAccessToken,
      igUsername: brand.igUsername,
    });
  });

  // ── PUT /api/instagram/posts/:postId/status — approve / reject ───────────────
  app.put("/api/instagram/posts/:postId/status", auth, async (req, reply) => {
    const { postId } = req.params as { postId: string };
    const { status } = z
      .object({ status: z.enum(["draft", "approved", "rejected", "published"]) })
      .parse(req.body);

    const post = await prisma.post.update({
      where: { id: postId },
      data: { status },
    });

    return reply.send({ post });
  });

  // ── POST /api/instagram/publish — publish a post NOW ─────────────────────────
  app.post("/api/instagram/publish", auth, async (req, reply) => {
    const userId = (req.user as { id: string }).id;

    const { postId, brandId, imageUrl, caption } = z
      .object({
        postId: z.string(),
        brandId: z.string(),
        imageUrl: z.string().url(),
        caption: z.string(),
      })
      .parse(req.body);

    // Verify brand ownership
    const brand = await prisma.brand.findFirst({ where: { id: brandId, userId } });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });

    if (!brand.igAccountId || !brand.igAccessToken) {
      return reply.code(400).send({
        message: "Instagram not connected. Connect Instagram in Brand Hub first.",
      });
    }

    // Check token expiry
    if (brand.igTokenExpiresAt && brand.igTokenExpiresAt < new Date()) {
      return reply.code(401).send({
        message: "Instagram token expired. Reconnect Instagram in Brand Hub.",
      });
    }

    const accessToken = decryptToken(brand.igAccessToken);

    try {
      // Step 1: Create media container
      const containerId = await createMediaContainer(
        brand.igAccountId,
        accessToken,
        imageUrl,
        caption
      );

      // Step 2: Wait for processing
      await waitForContainerReady(containerId, accessToken);

      // Step 3: Publish
      const mediaId = await publishMediaContainer(
        brand.igAccountId,
        accessToken,
        containerId
      );

      // Step 4: Update post status in DB
      await prisma.post.update({
        where: { id: postId },
        data: { status: "published" },
      });

      return reply.send({
        success: true,
        mediaId,
        message: "Published to Instagram successfully!",
      });
    } catch (err) {
      const message = (err as Error).message;
      return reply.code(500).send({ message: `Publish failed: ${message}` });
    }
  });

  // ── POST /api/instagram/publish-caption — publish caption-only (no image) ────
  // Useful for text/quote posts with a stock image URL
  app.post("/api/instagram/publish-caption", auth, async (req, reply) => {
    const userId = (req.user as { id: string }).id;

    const { postId, brandId, caption, imageUrl } = z
      .object({
        postId: z.string(),
        brandId: z.string(),
        caption: z.string(),
        imageUrl: z.string().url().optional(),
      })
      .parse(req.body);

    const brand = await prisma.brand.findFirst({ where: { id: brandId, userId } });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });

    if (!brand.igAccountId || !brand.igAccessToken) {
      return reply.code(400).send({ message: "Instagram not connected" });
    }

    const accessToken = decryptToken(brand.igAccessToken);
    const imgUrl = imageUrl ?? "https://placehold.co/1080x1080/6C3CE1/FFFFFF?text=Post";

    try {
      const containerId = await createMediaContainer(
        brand.igAccountId,
        accessToken,
        imgUrl,
        caption
      );
      await waitForContainerReady(containerId, accessToken);
      const mediaId = await publishMediaContainer(brand.igAccountId, accessToken, containerId);

      await prisma.post.update({ where: { id: postId }, data: { status: "published" } });

      return reply.send({ success: true, mediaId });
    } catch (err) {
      return reply.code(500).send({ message: (err as Error).message });
    }
  });

  // ── POST /api/instagram/schedule — queue a post for future publishing ────────
  app.post("/api/instagram/schedule", auth, async (req, reply) => {
    const userId = (req.user as { id: string }).id;

    const { postId, brandId, imageUrl, caption, scheduledAt } = z
      .object({
        postId:      z.string(),
        brandId:     z.string(),
        imageUrl:    z.string().url(),
        caption:     z.string(),
        scheduledAt: z.string().datetime(), // ISO 8601
      })
      .parse(req.body);

    const brand = await prisma.brand.findFirst({ where: { id: brandId, userId } });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });

    if (!brand.igAccountId || !brand.igAccessToken) {
      return reply.code(400).send({ message: "Instagram not connected" });
    }

    const scheduledDate = new Date(scheduledAt);
    const delay = scheduledDate.getTime() - Date.now();
    if (delay < 0) return reply.code(400).send({ message: "Scheduled time must be in the future" });

    // Queue with delay
    const job = await scheduleQueue.add(
      "publish-post",
      { postId, brandId, imageUrl, caption },
      { delay, jobId: `post-${postId}` }
    );

    // Update post in DB
    await prisma.post.update({
      where: { id: postId },
      data: {
        status: "scheduled",
        scheduledAt: scheduledDate,
        scheduleJobId: job.id ?? null,
      },
    });

    return reply.send({
      success: true,
      jobId: job.id,
      scheduledAt: scheduledDate,
      message: `Post scheduled for ${scheduledDate.toLocaleString()}`,
    });
  });

  // ── DELETE /api/instagram/schedule/:postId — cancel a scheduled post ─────────
  app.delete("/api/instagram/schedule/:postId", auth, async (req, reply) => {
    const { postId } = req.params as { postId: string };
    const userId = (req.user as { id: string }).id;

    const post = await prisma.post.findUnique({ where: { id: postId } });
    if (!post) return reply.code(404).send({ message: "Post not found" });

    // Remove from BullMQ
    if (post.scheduleJobId) {
      try {
        const job = await scheduleQueue.getJob(post.scheduleJobId);
        if (job) await job.remove();
      } catch { /* already processed */ }
    }

    // Reset post to approved
    await prisma.post.update({
      where: { id: postId },
      data: { status: "approved", scheduledAt: null, scheduleJobId: null },
    });

    return reply.send({ success: true, message: "Schedule cancelled" });
  });

  // ── GET /api/instagram/scheduled — list all upcoming scheduled posts ──────────
  app.get("/api/instagram/scheduled/:brandId", auth, async (req, reply) => {
    const { brandId } = req.params as { brandId: string };
    const userId = (req.user as { id: string }).id;

    const brand = await prisma.brand.findFirst({ where: { id: brandId, userId } });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });

    const scheduledPosts = await prisma.post.findMany({
      where: {
        status: "scheduled",
        agentRun: { brandId },
      },
      orderBy: { scheduledAt: "asc" },
    });

    return reply.send({ posts: scheduledPosts });
  });

  // ── GET /api/instagram/insights/:brandId — live IG insights ──────────────────
  app.get("/api/instagram/insights/:brandId", auth, async (req, reply) => {
    const { brandId } = req.params as { brandId: string };
    const userId = (req.user as { id: string }).id;

    const brand = await prisma.brand.findFirst({ where: { id: brandId, userId } });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });

    if (!brand.igAccountId || !brand.igAccessToken) {
      return reply.send({ connected: false, message: "Instagram not connected" });
    }

    const accessToken = decryptToken(brand.igAccessToken);

    try {
      // Fetch account basic info
      const accountRes = await fetch(
        `${GRAPH_BASE}/${brand.igAccountId}?fields=id,username,followers_count,media_count,biography&access_token=${accessToken}`
      );
      const account = (await accountRes.json()) as Record<string, unknown>;

      // Fetch recent media counts
      const mediaRes = await fetch(
        `${GRAPH_BASE}/${brand.igAccountId}/media?fields=id,like_count,comments_count,timestamp&limit=20&access_token=${accessToken}`
      );
      const mediaData = (await mediaRes.json()) as { data?: Array<Record<string, unknown>> };
      const posts = mediaData.data ?? [];

      const totalLikes = posts.reduce((s: number, p) => s + ((p.like_count as number) ?? 0), 0);
      const totalComments = posts.reduce((s: number, p) => s + ((p.comments_count as number) ?? 0), 0);
      const followers = (account.followers_count as number) ?? 0;
      const avgEngagement = followers > 0 && posts.length > 0
        ? parseFloat((((totalLikes + totalComments) / posts.length / followers) * 100).toFixed(2))
        : 0;

      return reply.send({
        connected: true,
        username: account.username,
        followers: account.followers_count,
        mediaCount: account.media_count,
        biography: account.biography,
        avgEngagementRate: avgEngagement,
        postsAnalyzed: posts.length,
        totalLikes30d: totalLikes,
        totalComments30d: totalComments,
      });
    } catch (err) {
      return reply.code(500).send({ message: (err as Error).message });
    }
  });
}
