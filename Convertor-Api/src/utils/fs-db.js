import fs from 'node:fs';
import path from 'node:path';
import { env } from '../config/env.js';

const dbPath = path.join(env.dataDir, 'db.json');
const defaultDb = {
  users: [],
  jobs: [],
  files: [],
  results: [],
  passwordResets: [],
  auditLogs: []
};

export function readDb() {
  if (!fs.existsSync(dbPath)) {
    fs.writeFileSync(dbPath, JSON.stringify(defaultDb, null, 2));
  }
  return JSON.parse(fs.readFileSync(dbPath, 'utf-8'));
}

export function writeDb(db) {
  fs.writeFileSync(dbPath, JSON.stringify(db, null, 2));
}

export function updateDb(mutator) {
  const db = readDb();
  const next = mutator(db) || db;
  writeDb(next);
  return next;
}
