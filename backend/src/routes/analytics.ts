import type { FastifyInstance } from "fastify";
import { prisma } from "../lib/prisma";

export async function analyticsRoutes(app: FastifyInstance) {
  const auth = { preHandler: [app.authenticate] };

  // GET /api/analytics/:brandId/latest
  app.get("/api/analytics/:brandId/latest", auth, async (req, reply) => {
    const user = req.user as { id: string };
    const { brandId } = req.params as { brandId: string };

    // Verify ownership
    const brand = await prisma.brand.findFirst({ where: { id: brandId, userId: user.id } });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });

    const report = await prisma.analyticsReport.findFirst({
      where: { brandId },
      orderBy: { createdAt: "desc" },
    });

    return reply.send({ report });
  });

  // GET /api/analytics/:brandId/history
  app.get("/api/analytics/:brandId/history", auth, async (req, reply) => {
    const user = req.user as { id: string };
    const { brandId } = req.params as { brandId: string };

    const brand = await prisma.brand.findFirst({ where: { id: brandId, userId: user.id } });
    if (!brand) return reply.code(404).send({ message: "Brand not found" });

    const history = await prisma.analyticsReport.findMany({
      where: { brandId },
      orderBy: { createdAt: "asc" },
      take: 30,
      select: {
        createdAt: true,
        avgEngagementRate: true,
        followerCount: true,
        avgReach: true,
      },
    });

    // Format for chart
    const formatted = history.map((h) => ({
      date: h.createdAt.toLocaleDateString("en-IN", { day: "numeric", month: "short" }),
      avgEngagementRate: h.avgEngagementRate ?? 0,
      followerCount: h.followerCount ?? 0,
      avgReach: h.avgReach ?? 0,
    }));

    return reply.send({ history: formatted });
  });
}
