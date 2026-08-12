import { readDb, updateDb } from '../utils/fs-db.js';

export const fileRepository = {
  mode: 'file',
  async init() { return true; },
  async findUserByEmailTenant(email, tenantKey) {
    return readDb().users.find((u) => u.email === email && u.tenantKey === tenantKey) || null;
  },
  async createUser(user) {
    updateDb((db) => { db.users.push(user); return db; });
    return user;
  },
  async createPasswordReset(reset) {
    updateDb((db) => { db.passwordResets.push(reset); return db; });
    return reset;
  },
  async findPasswordReset(token) {
    return readDb().passwordResets.find((r) => r.token === token && r.expiresAt > Date.now()) || null;
  },
  async updateUserPassword(userId, passwordHash) {
    updateDb((db) => {
      const user = db.users.find((u) => u.id === userId);
      if (user) user.passwordHash = passwordHash;
      return db;
    });
  },
  async deletePasswordReset(token) {
    updateDb((db) => {
      db.passwordResets = db.passwordResets.filter((r) => r.token !== token);
      return db;
    });
  },
  async createFile(file) {
    updateDb((db) => { db.files.push(file); return db; });
    return file;
  },
  async createJob(job) {
    updateDb((db) => { db.jobs.push(job); return db; });
    return job;
  },
  async updateJob(jobId, tenantKey, patch) {
    let updated = null;
    updateDb((db) => {
      const job = db.jobs.find((j) => j.id === jobId && j.tenantKey === tenantKey);
      if (job) {
        Object.assign(job, patch);
        updated = job;
      }
      return db;
    });
    return updated;
  },
  async findJob(jobId, tenantKey) {
    return readDb().jobs.find((j) => j.id === jobId && j.tenantKey === tenantKey) || null;
  },
  async findFile(fileId, tenantKey) {
    return readDb().files.find((f) => f.id === fileId && f.tenantKey === tenantKey) || null;
  },
  async createResult(result) {
    updateDb((db) => {
      db.results = db.results.filter((r) => r.jobId !== result.jobId);
      db.results.push(result);
      return db;
    });
    return result;
  },
  async findResultByJob(jobId, tenantKey) {
    return readDb().results.find((r) => r.jobId === jobId && r.tenantKey === tenantKey) || null;
  },
  async listJobs(tenantKey) {
    return readDb().jobs.filter((j) => j.tenantKey === tenantKey).sort((a,b) => b.createdAt.localeCompare(a.createdAt));
  },
  async logAudit(entry) {
    updateDb((db) => { db.auditLogs.push(entry); return db; });
    return entry;
  }
};
