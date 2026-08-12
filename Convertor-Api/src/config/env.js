import path from 'node:path';
import fs from 'node:fs';

const root = process.cwd();
const ensure = (p) => { fs.mkdirSync(p, { recursive: true }); return p; };
const toBool = (v, fallback = false) => {
  if (v == null) return fallback;
  return ['1', 'true', 'yes', 'on'].includes(String(v).toLowerCase());
};

export const env = {
  nodeEnv: process.env.NODE_ENV || 'development',
  port: Number(process.env.PORT || 4000),
  jwtSecret: process.env.JWT_SECRET || 'change_me',
  dataDir: ensure(path.resolve(root, process.env.DATA_DIR || './storage')),
  uploadsDir: ensure(path.resolve(root, process.env.UPLOADS_DIR || './storage/uploads')),
  databaseUrl: process.env.DATABASE_URL || '',
  dbMode: process.env.DATABASE_URL ? 'postgres' : 'file',
  requestWindowMs: Number(process.env.REQUEST_WINDOW_MS || 60_000),
  requestMaxPerWindow: Number(process.env.REQUEST_MAX_PER_WINDOW || 120),
  authMaxPerWindow: Number(process.env.AUTH_MAX_PER_WINDOW || 15),
  uploadMaxBytes: Number(process.env.UPLOAD_MAX_BYTES || 25 * 1024 * 1024),
  uploadMaxFiles: Number(process.env.UPLOAD_MAX_FILES || 10),
  allowResetTokenInResponse: toBool(process.env.ALLOW_RESET_TOKEN_IN_RESPONSE, true)
};
