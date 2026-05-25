import { Redis } from "ioredis";

const REDIS_URL = process.env.REDIS_URL!;
const isTLS = REDIS_URL.startsWith("rediss://");

export const redis = new Redis(REDIS_URL, {
  maxRetriesPerRequest: null, // Required for BullMQ
  enableReadyCheck: false,
  lazyConnect: true,
  // Only enable TLS for Upstash (rediss://) — not for plain Railway Redis (redis://)
  ...(isTLS ? { tls: { rejectUnauthorized: false } } : {}),
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
