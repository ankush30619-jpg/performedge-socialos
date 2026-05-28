/**
 * scheduleWorker.ts
 * Processes delayed BullMQ jobs to publish Instagram posts at scheduled times.
 */
import { Worker } from "bullmq";
import { redis } from "../lib/redis";
import { prisma } from "../lib/prisma";
import crypto from "crypto";

const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY!;
const GRAPH_BASE = "https://graph.facebook.com/v21.0";

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

async function publishToIG(
  igAccountId: string,
  accessToken: string,
  imageUrl: string,
  caption: string
): Promise<string> {
  // Create container
  const createRes = await fetch(`${GRAPH_BASE}/${igAccountId}/media`, {
    method: "POST",
    body: new URLSearchParams({ image_url: imageUrl, caption, access_token: accessToken, media_type: "IMAGE" }),
  });
  const created = (await createRes.json()) as { id?: string; error?: { message: string } };
  if (!created.id) throw new Error(created.error?.message ?? "Container creation failed");

  // Wait for FINISHED
  for (let i = 0; i < 12; i++) {
    const statusRes = await fetch(`${GRAPH_BASE}/${created.id}?fields=status_code&access_token=${accessToken}`);
    const status = (await statusRes.json()) as { status_code?: string };
    if (status.status_code === "FINISHED") break;
    if (status.status_code === "ERROR") throw new Error("Media processing failed");
    await new Promise((r) => setTimeout(r, 2500));
  }

  // Publish
  const pubRes = await fetch(`${GRAPH_BASE}/${igAccountId}/media_publish`, {
    method: "POST",
    body: new URLSearchParams({ creation_id: created.id, access_token: accessToken }),
  });
  const pub = (await pubRes.json()) as { id?: string; error?: { message: string } };
  if (!pub.id) throw new Error(pub.error?.message ?? "Publish failed");
  return pub.id;
}

export function startScheduleWorker() {
  const worker = new Worker(
    "instagram-schedule",
    async (job) => {
      const { postId, brandId, imageUrl, caption } = job.data as {
        postId: string;
        brandId: string;
        imageUrl: string;
        caption: string;
      };

      console.log(`[ScheduleWorker] Publishing post ${postId} for brand ${brandId}`);

      // Fetch brand
      const brand = await prisma.brand.findUnique({ where: { id: brandId } });
      if (!brand?.igAccountId || !brand.igAccessToken) {
        throw new Error("Brand has no Instagram credentials");
      }

      if (brand.igTokenExpiresAt && brand.igTokenExpiresAt < new Date()) {
        throw new Error("Instagram token expired — reconnect in Brand Hub");
      }

      const accessToken = decryptToken(brand.igAccessToken);

      const mediaId = await publishToIG(brand.igAccountId, accessToken, imageUrl, caption);

      // Mark post as published — persist igMediaId + publishedAt so the
      // performance comparison report can pull live engagement per post.
      await prisma.post.update({
        where: { id: postId },
        data: {
          status:      "published",
          igMediaId:   mediaId,
          publishedAt: new Date(),
        },
      });

      console.log(`[ScheduleWorker] Post ${postId} published → Media ID ${mediaId}`);
      return { mediaId };
    },
    {
      connection: redis,
      concurrency: 3,
    }
  );

  worker.on("completed", (job) => {
    console.log(`[ScheduleWorker] Job ${job.id} completed`);
  });

  worker.on("failed", (job, err) => {
    console.error(`[ScheduleWorker] Job ${job?.id} failed: ${err.message}`);
    // Mark post as draft so user can retry
    if (job?.data?.postId) {
      prisma.post
        .update({ where: { id: job.data.postId }, data: { status: "approved" } })
        .catch(() => {});
    }
  });

  console.log("   Schedule worker   →  running");
  return worker;
}
