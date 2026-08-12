import { env } from '../config/env.js';

const buckets = new Map();

function keyFromReq(req) {
  return `${req.ip}:${req.baseUrl || ''}`;
}

function evaluate(key, max) {
  const now = Date.now();
  const current = buckets.get(key);
  if (!current || current.resetAt <= now) {
    const next = { count: 1, resetAt: now + env.requestWindowMs };
    buckets.set(key, next);
    return next;
  }
  current.count += 1;
  return current;
}

export function rateLimit({ max = env.requestMaxPerWindow } = {}) {
  return (req, res, next) => {
    const bucket = evaluate(keyFromReq(req), max);
    res.setHeader('X-RateLimit-Limit', String(max));
    res.setHeader('X-RateLimit-Remaining', String(Math.max(0, max - bucket.count)));
    if (bucket.count > max) {
      res.setHeader('Retry-After', String(Math.ceil((bucket.resetAt - Date.now()) / 1000)));
      const error = new Error('Rate limit overschreden');
      error.statusCode = 429;
      next(error);
      return;
    }
    next();
  };
}

export function authRateLimit() {
  return rateLimit({ max: env.authMaxPerWindow });
}
