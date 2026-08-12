import { query, ensureSchema } from '../db/postgres.js';

function mapUser(row) {
  if (!row) return null;
  return {
    id: row.id,
    email: row.email,
    passwordHash: row.password_hash,
    tenantKey: row.tenant_key,
    name: row.name,
    role: row.role,
    createdAt: row.created_at?.toISOString?.() || row.created_at
  };
}

function mapFile(row) {
  if (!row) return null;
  return {
    id: row.id,
    tenantKey: row.tenant_key,
    path: row.path,
    originalname: row.original_name,
    size: Number(row.size),
    createdAt: row.created_at?.toISOString?.() || row.created_at
  };
}

function mapJob(row) {
  if (!row) return null;
  return {
    id: row.id,
    fileId: row.file_id,
    tenantKey: row.tenant_key,
    status: row.status,
    error: row.error,
    createdAt: row.created_at?.toISOString?.() || row.created_at,
    updatedAt: row.updated_at?.toISOString?.() || row.updated_at
  };
}

function mapResult(row) {
  if (!row) return null;
  const payload = row.payload || {};
  return {
    id: row.id,
    jobId: row.job_id,
    tenantKey: row.tenant_key,
    format: row.format,
    source: payload.source,
    model: payload.model,
    metrics: payload.metrics,
    findings: payload.findings,
    analysis: payload.analysis,
    viewer: payload.viewer,
    confidence: Number(row.confidence),
    dxfPath: row.dxf_path,
    createdAt: row.created_at?.toISOString?.() || row.created_at
  };
}

export const postgresRepository = {
  mode: 'postgres',
  async init() { return ensureSchema(); },
  async findUserByEmailTenant(email, tenantKey) {
    const { rows } = await query('SELECT * FROM users WHERE email=$1 AND tenant_key=$2 LIMIT 1', [email, tenantKey]);
    return mapUser(rows[0]);
  },
  async createUser(user) {
    await query(
      'INSERT INTO users (id, email, password_hash, tenant_key, name, role, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7)',
      [user.id, user.email, user.passwordHash, user.tenantKey, user.name, user.role, user.createdAt]
    );
    return user;
  },
  async createPasswordReset(reset) {
    await query('INSERT INTO password_resets (id, token, user_id, expires_at) VALUES ($1,$2,$3,$4)', [reset.id, reset.token, reset.userId, reset.expiresAt]);
    return reset;
  },
  async findPasswordReset(token) {
    const { rows } = await query('SELECT * FROM password_resets WHERE token=$1 AND expires_at > $2 LIMIT 1', [token, Date.now()]);
    return rows[0] ? { id: rows[0].id, token: rows[0].token, userId: rows[0].user_id, expiresAt: Number(rows[0].expires_at) } : null;
  },
  async updateUserPassword(userId, passwordHash) {
    await query('UPDATE users SET password_hash=$2 WHERE id=$1', [userId, passwordHash]);
  },
  async deletePasswordReset(token) {
    await query('DELETE FROM password_resets WHERE token=$1', [token]);
  },
  async createFile(file) {
    await query('INSERT INTO files (id, tenant_key, path, original_name, size, created_at) VALUES ($1,$2,$3,$4,$5,$6)', [file.id, file.tenantKey, file.path, file.originalname, file.size, file.createdAt]);
    return file;
  },
  async createJob(job) {
    await query('INSERT INTO jobs (id, file_id, tenant_key, status, error, created_at, updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7)', [job.id, job.fileId, job.tenantKey, job.status, job.error || null, job.createdAt, job.updatedAt]);
    return job;
  },
  async updateJob(jobId, tenantKey, patch) {
    const current = await this.findJob(jobId, tenantKey);
    if (!current) return null;
    const next = { ...current, ...patch };
    await query('UPDATE jobs SET status=$3, error=$4, updated_at=$5 WHERE id=$1 AND tenant_key=$2', [jobId, tenantKey, next.status, next.error || null, next.updatedAt]);
    return next;
  },
  async findJob(jobId, tenantKey) {
    const { rows } = await query('SELECT * FROM jobs WHERE id=$1 AND tenant_key=$2 LIMIT 1', [jobId, tenantKey]);
    return mapJob(rows[0]);
  },
  async findFile(fileId, tenantKey) {
    const { rows } = await query('SELECT * FROM files WHERE id=$1 AND tenant_key=$2 LIMIT 1', [fileId, tenantKey]);
    return mapFile(rows[0]);
  },
  async createResult(result) {
    await query(
      'INSERT INTO results (id, job_id, tenant_key, format, payload, confidence, dxf_path, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT (job_id) DO UPDATE SET payload=EXCLUDED.payload, confidence=EXCLUDED.confidence, dxf_path=EXCLUDED.dxf_path, format=EXCLUDED.format',
      [result.id, result.jobId, result.tenantKey, result.format, JSON.stringify({ source: result.source, model: result.model, metrics: result.metrics, findings: result.findings, analysis: result.analysis, viewer: result.viewer }), result.confidence, result.dxfPath, result.createdAt]
    );
    return result;
  },
  async findResultByJob(jobId, tenantKey) {
    const { rows } = await query('SELECT * FROM results WHERE job_id=$1 AND tenant_key=$2 LIMIT 1', [jobId, tenantKey]);
    return mapResult(rows[0]);
  },
  async listJobs(tenantKey) {
    const { rows } = await query('SELECT * FROM jobs WHERE tenant_key=$1 ORDER BY created_at DESC', [tenantKey]);
    return rows.map(mapJob);
  },
  async logAudit(entry) {
    await query('INSERT INTO audit_logs (id, event, payload, created_at) VALUES ($1,$2,$3,$4)', [entry.id, entry.event, JSON.stringify(entry.payload || {}), entry.createdAt]);
    return entry;
  }
};
