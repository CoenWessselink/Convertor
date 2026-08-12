import { randomUUID } from 'node:crypto';
import { repository } from '../repositories/index.js';

export async function logAudit(event, payload = {}) {
  return repository.logAudit({
    id: randomUUID(),
    event,
    payload,
    createdAt: new Date().toISOString()
  });
}
