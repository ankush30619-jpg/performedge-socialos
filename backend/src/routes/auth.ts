import type { FastifyInstance } from "fastify";
import bcrypt from "bcryptjs";
import { prisma } from "../lib/prisma";
import { z } from "zod";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
});

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().optional(),
});

export async function authRoutes(app: FastifyInstance) {
  // POST /api/auth/login
  app.post("/api/auth/login", async (req, reply) => {
    const body = loginSchema.parse(req.body);

    const user = await prisma.user.findUnique({ where: { email: body.email } });
    if (!user) return reply.code(401).send({ message: "Invalid credentials" });

    const valid = await bcrypt.compare(body.password, user.passwordHash);
    if (!valid) return reply.code(401).send({ message: "Invalid credentials" });

    const token = app.jwt.sign(
      { id: user.id, email: user.email, role: user.role },
      { expiresIn: "7d" }
    );

    return reply.send({
      user: { id: user.id, email: user.email, name: user.name, role: user.role },
      token,
    });
  });

  // POST /api/auth/register (internal — creates first admin)
  app.post("/api/auth/register", async (req, reply) => {
    const body = registerSchema.parse(req.body);

    const existing = await prisma.user.findUnique({ where: { email: body.email } });
    if (existing) return reply.code(409).send({ message: "Email already registered" });

    const passwordHash = await bcrypt.hash(body.password, 12);
    const user = await prisma.user.create({
      data: { email: body.email, passwordHash, name: body.name },
    });

    const token = app.jwt.sign(
      { id: user.id, email: user.email, role: user.role },
      { expiresIn: "7d" }
    );

    return reply.code(201).send({
      user: { id: user.id, email: user.email, name: user.name, role: user.role },
      token,
    });
  });

  // GET /api/auth/me (protected)
  app.get("/api/auth/me", { preHandler: [app.authenticate] }, async (req, reply) => {
    const payload = req.user as { id: string };
    const user = await prisma.user.findUnique({ where: { id: payload.id } });
    if (!user) return reply.code(404).send({ message: "User not found" });
    return reply.send({ user: { id: user.id, email: user.email, name: user.name } });
  });

  // POST /api/auth/change-password (protected)
  app.post("/api/auth/change-password", { preHandler: [app.authenticate] }, async (req, reply) => {
    const payload = req.user as { id: string };
    const { currentPassword, newPassword } = z.object({
      currentPassword: z.string().min(1),
      newPassword: z.string().min(8),
    }).parse(req.body);

    const user = await prisma.user.findUnique({ where: { id: payload.id } });
    if (!user) return reply.code(404).send({ message: "User not found" });

    const valid = await bcrypt.compare(currentPassword, user.passwordHash);
    if (!valid) return reply.code(401).send({ message: "Current password is incorrect" });

    const newHash = await bcrypt.hash(newPassword, 12);
    await prisma.user.update({ where: { id: user.id }, data: { passwordHash: newHash } });

    return reply.send({ message: "Password updated successfully" });
  });
}
