import type { FastifyInstance } from "fastify";
import { prisma } from "../lib/prisma";
import crypto from "crypto";
import { z } from "zod";

const META_APP_ID = process.env.META_APP_ID!;
const META_APP_SECRET = process.env.META_APP_SECRET!;
const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY!; // base64 AES-256
const NEXTAUTH_URL = process.env.NEXTAUTH_URL ?? "http://localhost:3000";
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

// ── AES-256-GCM encrypt / decrypt ─────────────────────────────────────────────

function encryptToken(token: string): string {
  const keyBuf = Buffer.from(ENCRYPTION_KEY, "base64");
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", keyBuf, iv);
  const enc = Buffer.concat([cipher.update(token, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, tag, enc]).toString("base64");
}

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

// ── OAuth state store (in-memory, short TTL) ──────────────────────────────────
// In prod you'd use Redis; here a Map + 10-min expiry is fine

const stateStore = new Map<string, { brandId: string; userId: string; expiresAt: number }>();

function makeState(brandId: string, userId: string) {
  const state = crypto.randomBytes(16).toString("hex");
  stateStore.set(state, { brandId, userId, expiresAt: Date.now() + 10 * 60 * 1000 });
  return state;
}

function consumeState(state: string) {
  const entry = stateStore.get(state);
  if (!entry) return null;
  stateStore.delete(state);
  if (Date.now() > entry.expiresAt) return null;
  return entry;
}

// ── Route definitions ──────────────────────────────────────────────────────────

export async function metaRoutes(app: FastifyInstance) {

  // GET /api/meta/auth-url?brandId=xxx
  // Returns the Meta OAuth dialog URL with CSRF state
  app.get(
    "/api/meta/auth-url",
    { preHandler: [app.authenticate] },
    async (req, reply) => {
      const { brandId } = z.object({ brandId: z.string() }).parse(req.query);
      const userId = (req.user as { id: string }).id;

      const state = makeState(brandId, userId);
      const redirectUri = `${BACKEND_URL}/api/meta/callback`;

      const params = new URLSearchParams({
        client_id: META_APP_ID,
        redirect_uri: redirectUri,
        scope: [
          "instagram_basic",
          "instagram_content_publish",
          "instagram_manage_comments",
          "instagram_manage_insights",
          "pages_show_list",
          "pages_read_engagement",
          "business_management",
        ].join(","),
        response_type: "code",
        state,
      });

      return reply.send({
        url: `https://www.facebook.com/v21.0/dialog/oauth?${params}`,
        state,
      });
    }
  );

  // GET /api/meta/callback?code=xxx&state=xxx
  // Meta redirects here after user authorises — exchanges code, stores token
  app.get("/api/meta/callback", async (req, reply) => {
    const { code, state, error, error_description } = req.query as Record<string, string>;

    const frontendUrl = NEXTAUTH_URL;

    if (error) {
      return reply.redirect(
        `${frontendUrl}/brands?meta_error=${encodeURIComponent(error_description ?? error)}`
      );
    }

    const entry = consumeState(state);
    if (!entry) {
      return reply.redirect(`${frontendUrl}/brands?meta_error=invalid_state`);
    }

    const redirectUri = `${BACKEND_URL}/api/meta/callback`;

    // Exchange code → short-lived user access token
    const tokenRes = await fetch(
      `https://graph.facebook.com/v21.0/oauth/access_token?` +
        new URLSearchParams({
          client_id: META_APP_ID,
          client_secret: META_APP_SECRET,
          redirect_uri: redirectUri,
          code,
        })
    );
    const tokenData = await tokenRes.json() as { access_token?: string; error?: { message: string } };

    if (!tokenData.access_token) {
      const msg = tokenData.error?.message ?? "token_exchange_failed";
      return reply.redirect(`${frontendUrl}/brands?meta_error=${encodeURIComponent(msg)}`);
    }

    // Exchange short-lived → long-lived user token (60 days)
    const llRes = await fetch(
      `https://graph.facebook.com/v21.0/oauth/access_token?` +
        new URLSearchParams({
          grant_type: "fb_exchange_token",
          client_id: META_APP_ID,
          client_secret: META_APP_SECRET,
          fb_exchange_token: tokenData.access_token,
        })
    );
    const llData = await llRes.json() as { access_token?: string; expires_in?: number };
    const longLivedToken = llData.access_token ?? tokenData.access_token;

    // Fetch connected Instagram Business accounts via /me/accounts
    const pagesRes = await fetch(
      `https://graph.facebook.com/v21.0/me/accounts?fields=id,name,instagram_business_account{id,username,name,profile_picture_url,followers_count}&access_token=${longLivedToken}`
    );
    const pagesData = await pagesRes.json() as {
      data?: Array<{
        id: string; name: string;
        instagram_business_account?: { id: string; username: string; name: string; profile_picture_url?: string; followers_count?: number };
      }>
    };

    // Find first page with linked IG business account
    const igAccount = pagesData.data?.find((p) => p.instagram_business_account)?.instagram_business_account;

    // Encrypt and persist
    const encrypted = encryptToken(longLivedToken);
    const tokenExpiresAt = new Date(Date.now() + (llData.expires_in ?? 5184000) * 1000);

    await prisma.brand.update({
      where: { id: entry.brandId },
      data: {
        igAccessToken: encrypted,
        igTokenExpiresAt: tokenExpiresAt,
        igAccountId: igAccount?.id ?? null,
        igUsername: igAccount?.username ?? null,
        igFollowers: igAccount?.followers_count ?? null,
      },
    });

    return reply.redirect(
      `${frontendUrl}/brands?meta_success=1&ig_user=${encodeURIComponent(igAccount?.username ?? "connected")}`
    );
  });

  // POST /api/meta/manual-connect
  // Simple token-based connection — paste Page Access Token + optional IG Account ID + optional Page ID
  // Pass testOnly: true to validate without saving to DB
  app.post(
    "/api/meta/manual-connect",
    { preHandler: [app.authenticate] },
    async (req, reply) => {
      const { brandId, accessToken, igAccountId, pageId, testOnly } = z.object({
        brandId:     z.string(),
        accessToken: z.string().min(10),
        igAccountId: z.string().optional(),
        pageId:      z.string().optional(),
        testOnly:    z.boolean().optional(),
      }).parse(req.body);

      let igId       = igAccountId ?? "";
      let igUsername = "";
      let igFollowers = 0;
      let resolvedPageId   = pageId ?? "";
      let resolvedPageName = "";

      try {
        if (igId) {
          // Fetch IG details directly using the provided account ID
          const igRes  = await fetch(
            `https://graph.facebook.com/v21.0/${igId}?fields=username,followers_count,name&access_token=${accessToken}`
          );
          const igData = await igRes.json() as {
            username?: string; followers_count?: number; error?: { message: string };
          };
          if (igData.error) {
            return reply.code(400).send({ message: `Meta API error: ${igData.error.message}` });
          }
          igUsername  = igData.username  ?? "";
          igFollowers = igData.followers_count ?? 0;

          // If pageId was provided, fetch the page name too
          if (resolvedPageId) {
            try {
              const pageRes  = await fetch(
                `https://graph.facebook.com/v21.0/${resolvedPageId}?fields=name&access_token=${accessToken}`
              );
              const pageData = await pageRes.json() as { name?: string };
              resolvedPageName = pageData.name ?? "";
            } catch { /* non-fatal */ }
          }
        } else {
          // Auto-discover IG account from Facebook Pages linked to this token
          const pagesRes  = await fetch(
            `https://graph.facebook.com/v21.0/me/accounts?fields=id,name,instagram_business_account{id,username,followers_count}&access_token=${accessToken}`
          );
          const pagesData = await pagesRes.json() as {
            data?: Array<{
              id: string; name: string;
              instagram_business_account?: { id: string; username: string; followers_count?: number };
            }>;
            error?: { message: string };
          };
          if (pagesData.error) {
            return reply.code(400).send({ message: `Meta API error: ${pagesData.error.message}` });
          }
          const page  = pagesData.data?.find(p => p.instagram_business_account);
          const igAcc = page?.instagram_business_account;
          if (!igAcc) {
            return reply.code(400).send({
              message: "No Instagram Business Account found. Make sure this is a Page Access Token linked to an Instagram Business account.",
            });
          }
          igId             = igAcc.id;
          igUsername       = igAcc.username;
          igFollowers      = igAcc.followers_count ?? 0;
          resolvedPageId   = page?.id   ?? "";
          resolvedPageName = page?.name ?? "";
        }
      } catch {
        return reply.code(500).send({ message: "Failed to validate token with Meta API" });
      }

      // If testOnly: true — return the validated data without saving
      if (testOnly) {
        return reply.send({
          success: true,
          igAccountId: igId,
          igUsername,
          igFollowers,
          pageId:   resolvedPageId,
          pageName: resolvedPageName,
        });
      }

      // Try to exchange short-lived token → long-lived (60-day) token
      // If user pasted a short-lived token from Graph API Explorer, this saves them from
      // a same-day expiry. If the token is already long-lived, exchange is idempotent.
      let finalToken = accessToken;
      let tokenExpiresAt = new Date(Date.now() + 60 * 24 * 60 * 60 * 1000); // assume 60d
      try {
        const llRes = await fetch(
          `https://graph.facebook.com/v21.0/oauth/access_token?` +
            new URLSearchParams({
              grant_type:        "fb_exchange_token",
              client_id:         META_APP_ID,
              client_secret:     META_APP_SECRET,
              fb_exchange_token: accessToken,
            })
        );
        const llData = await llRes.json() as { access_token?: string; expires_in?: number; error?: { message: string } };
        if (llData.access_token) {
          finalToken     = llData.access_token;
          tokenExpiresAt = new Date(Date.now() + (llData.expires_in ?? 5184000) * 1000);
          console.log(`[Meta] Long-lived token exchange OK for brand ${brandId} — expires ${tokenExpiresAt.toISOString()}`);
        } else if (llData.error) {
          console.warn(`[Meta] Long-lived exchange failed for brand ${brandId}: ${llData.error.message} — saving original token`);
        }
      } catch (e) {
        console.warn(`[Meta] Long-lived exchange threw for brand ${brandId}:`, (e as Error).message);
      }

      // Encrypt & persist
      const encrypted = encryptToken(finalToken);

      await prisma.brand.update({
        where: { id: brandId },
        data: {
          igAccountId:      igId,
          igAccessToken:    encrypted,
          igTokenExpiresAt: tokenExpiresAt,
          igUsername,
          igFollowers,
        },
      });

      return reply.send({
        success:     true,
        igAccountId: igId,
        igUsername,
        igFollowers,
        pageId:      resolvedPageId,
        pageName:    resolvedPageName,
      });
    }
  );

  // POST /api/meta/disconnect
  // Removes IG credentials for a brand
  app.post(
    "/api/meta/disconnect",
    { preHandler: [app.authenticate] },
    async (req, reply) => {
      const { brandId } = z.object({ brandId: z.string() }).parse(req.body);

      await prisma.brand.update({
        where: { id: brandId },
        data: {
          igAccessToken: null,
          igTokenExpiresAt: null,
          igAccountId: null,
          igUsername: null,
          igFollowers: null,
        },
      });

      return reply.send({ success: true });
    }
  );

  // GET /api/meta/status/:brandId
  // Returns IG connection status for a brand
  app.get(
    "/api/meta/status/:brandId",
    { preHandler: [app.authenticate] },
    async (req, reply) => {
      const { brandId } = req.params as { brandId: string };
      const brand = await prisma.brand.findUnique({
        where: { id: brandId },
        select: {
          igAccountId: true,
          igUsername: true,
          igFollowers: true,
          igTokenExpiresAt: true,
          igAccessToken: true,
        },
      });

      if (!brand) return reply.code(404).send({ message: "Brand not found" });

      const connected = !!brand.igAccessToken;
      const expired = brand.igTokenExpiresAt ? brand.igTokenExpiresAt < new Date() : false;

      return reply.send({
        connected,
        expired,
        igUsername: brand.igUsername,
        igAccountId: brand.igAccountId,
        igFollowers: brand.igFollowers,
        expiresAt: brand.igTokenExpiresAt,
      });
    }
  );

  // POST /api/meta/refresh/:brandId
  // Refreshes an expiring long-lived token
  app.post(
    "/api/meta/refresh/:brandId",
    { preHandler: [app.authenticate] },
    async (req, reply) => {
      const { brandId } = req.params as { brandId: string };
      const brand = await prisma.brand.findUnique({ where: { id: brandId } });
      if (!brand?.igAccessToken) return reply.code(400).send({ message: "No token to refresh" });

      const currentToken = decryptToken(brand.igAccessToken);

      const res = await fetch(
        `https://graph.facebook.com/v21.0/oauth/access_token?` +
          new URLSearchParams({
            grant_type: "fb_exchange_token",
            client_id: META_APP_ID,
            client_secret: META_APP_SECRET,
            fb_exchange_token: currentToken,
          })
      );
      const data = await res.json() as { access_token?: string; expires_in?: number; error?: { message: string } };
      if (!data.access_token) {
        return reply.code(500).send({ message: data.error?.message ?? "refresh_failed" });
      }

      const encrypted = encryptToken(data.access_token);
      const tokenExpiresAt = new Date(Date.now() + (data.expires_in ?? 5184000) * 1000);

      await prisma.brand.update({
        where: { id: brandId },
        data: { igAccessToken: encrypted, igTokenExpiresAt: tokenExpiresAt },
      });

      return reply.send({ success: true, expiresAt: tokenExpiresAt });
    }
  );
}
