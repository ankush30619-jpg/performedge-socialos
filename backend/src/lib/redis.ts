import { Redis } from "ioredis";

// Upstash Redis requires TLS — swap redis:// → rediss://
const rawUrl = process.env.REDIS_URL!;
const REDIS_URL = rawUrl.startsWith("redis://")
  ? rawUrl.replace("redis://", "rediss://")
  : rawUrl;

export const redis = new Redis(REDIS_URL, {
  maxRetriesPerRequest: null, // Required for BullMQ
  enableReadyCheck: false,
  lazyConnect: true,
  tls: {
    rejectUnauthorized: false, // Upstash self-signed cert
  },
  retryStrategy: (times) => {
    if (times > 5) return null; // stop retrying after 5 attempts
    return Math.min(times * 500, 3000);
  },
});

redis.on("error", (err) => {
  // Only log first occurrence to avoid log spam
  if (!process.env._REDIS_ERR_LOGGED) {
    console.error("[Redis] Connection error:", err.message);
    process.env._REDIS_ERR_LOGGED = "1";
  }
});

redis.on("connect", () => {
  delete process.env._REDIS_ERR_LOGGED;
  console.log("[Redis] Connected");
});
