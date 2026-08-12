import fs from 'node:fs';
import path from 'node:path';
import { Pool } from 'pg';
import { env } from '../config/env.js';

let pool;

export function hasPostgres() {
  return Boolean(env.databaseUrl);
}

export function getPool() {
  if (!hasPostgres()) {
    throw new Error('DATABASE_URL ontbreekt');
  }
  if (!pool) {
    pool = new Pool({ connectionString: env.databaseUrl });
  }
  return pool;
}

export async function query(text, params = []) {
  return getPool().query(text, params);
}

export async function ensureSchema() {
  if (!hasPostgres()) return false;
  const sqlPath = path.resolve(process.cwd(), 'src/db/schema.sql');
  const sql = fs.readFileSync(sqlPath, 'utf-8');
  await query(sql);
  return true;
}

export async function closePool() {
  if (pool) {
    await pool.end();
    pool = undefined;
  }
}
