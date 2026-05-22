import { Worker } from "bullmq";
import { redis } from "../lib/redis";
import { prisma } from "../lib/prisma";
import { Prisma } from "@prisma/client";
import axios from "axios";
import crypto from "crypto";

const AGENTS_URL = process.env.NEXT_PUBLIC_AGENTS_URL ?? "http://localhost:8000";

// ── Token decryption (same as meta.ts / instagram.ts) ─────────────────────────
function decryptToken(encrypted: string): string {
  const key = Buffer.from(process.env.ENCRYPTION_KEY ?? "", "base64");
  const buf = Buffer.from(encrypted, "base64");
  const iv      = buf.subarray(0, 12);
  const tag     = buf.subarray(12, 28);
  const cipher  = buf.subarray(28);
  const dec = crypto.createDecipheriv("aes-256-gcm", key, iv);
  dec.setAuthTag(tag);
  return Buffer.concat([dec.update(cipher), dec.final()]).toString("utf8");
}

export function startLearningWorker() {
  const worker = new Worker(
    "brand-learning",
    async (job) => {
      const { brandId, trigger } = job.data;

      console.log(`[LearningWorker] Re-learning ${brandId ? `brand ${brandId}` : "all brands"} — trigger: ${trigger}`);

      let brandIds: string[] = [];

      if (brandId) {
        brandIds = [brandId];
      } else {
        // Cron: re-learn ALL brands
        const all = await prisma.brand.findMany({ select: { id: true } });
        brandIds = all.map((b) => b.id);
      }

      for (const id of brandIds) {
        try {
          // Fetch full brand record including encrypted token
          const brand = await prisma.brand.findUnique({ where: { id } });
          if (!brand) {
            console.warn(`[LearningWorker] Brand ${id} not found — skipping`);
            continue;
          }

          // Decrypt IG token if present
          let igAccessToken: string | null = null;
          if (brand.igAccessToken) {
            try {
              igAccessToken = decryptToken(brand.igAccessToken);
            } catch {
              console.warn(`[LearningWorker] Could not decrypt token for brand ${id}`);
            }
          }

          // Call Python agents relearn endpoint with full brand context
          const response = await axios.post(
            `${AGENTS_URL}/brands/${id}/relearn`,
            {
              trigger,
              brand: {
                id:             brand.id,
                name:           brand.name,
                niche:          brand.niche,
                website:        brand.website,
                targetAudience: brand.targetAudience,
                tone:           brand.tone,
                igAccountId:    brand.igAccountId,
                igAccessToken,            // decrypted — passed securely over internal network
                igUsername:     brand.igUsername,
                igFollowers:    brand.igFollowers,
                knowledgeJson:  brand.knowledgeJson,
              },
            },
            { timeout: 120_000 }         // 2 min — analyst + research can be slow
          );

          const data = response.data as {
            summary?: string;
            knowledgeJson?: Record<string, unknown>;
            analystReport?: Record<string, unknown>;
            researchData?: Record<string, unknown>;
          };

          // Update brand knowledgeJson with fresh insights
          if (data.knowledgeJson) {
            await prisma.brand.update({
              where: { id },
              data: { knowledgeJson: data.knowledgeJson as Prisma.InputJsonValue },
            });
          }

          // Persist learning log
          const summary = data.summary ?? "Re-learn completed";
          await prisma.brandLearningLog.create({
            data: {
              brandId: id,
              trigger,
              summary,
              rawData: {
                analystReport: (data.analystReport ?? null) as Prisma.InputJsonValue,
                researchData:  (data.researchData  ?? null) as Prisma.InputJsonValue,
                knowledgeJson: (data.knowledgeJson ?? null) as Prisma.InputJsonValue,
              } as Prisma.InputJsonValue,
            },
          });

          // Also persist analyst report to AnalyticsReport table if we got live data
          if (data.analystReport) {
            const r = data.analystReport as Record<string, unknown>;
            await prisma.analyticsReport.create({
              data: {
                brandId:          id,
                followerCount:    typeof r.followerCount    === "number" ? r.followerCount    : null,
                avgReach:         typeof r.avgReach         === "number" ? r.avgReach         : null,
                avgEngagementRate:typeof r.avgEngagementRate=== "number" ? r.avgEngagementRate: null,
                postsAnalyzed:    typeof r.postsAnalyzed    === "number" ? r.postsAnalyzed    : null,
                rawReport:        r as Prisma.InputJsonValue,
              },
            });
          }

          console.log(`[LearningWorker] Brand ${id} re-learned: ${summary}`);
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Unknown error";
          console.error(`[LearningWorker] Brand ${id} re-learn failed:`, msg);

          await prisma.brandLearningLog.create({
            data: { brandId: id, trigger, summary: `Failed: ${msg}` },
          });
        }
      }
    },
    { connection: redis, concurrency: 2 }
  );

  worker.on("failed", (job, err) => {
    console.error(`[LearningWorker] Job ${job?.id} failed:`, err.message);
  });

  console.log("[LearningWorker] Brand learning worker started");
  return worker;
}
