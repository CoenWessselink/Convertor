import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { randomUUID } from 'node:crypto';
import { env } from '../config/env.js';
import { repository } from '../repositories/index.js';
import { logAudit } from './audit-service.js';

export async function register({ email, password, tenantKey, name }) {
  const normalizedEmail = String(email || '').trim().toLowerCase();
  const normalizedTenant = String(tenantKey || '').trim().toLowerCase();
  if (!normalizedEmail || !password || !normalizedTenant) throw new Error('Ontbrekende velden');
  if (password.length < 8) throw new Error('Wachtwoord moet minimaal 8 tekens zijn');
  const existing = await repository.findUserByEmailTenant(normalizedEmail, normalizedTenant);
  if (existing) throw new Error('Gebruiker bestaat al');
  const passwordHash = await bcrypt.hash(password, 10);
  const user = {
    id: randomUUID(),
    email: normalizedEmail,
    passwordHash,
    tenantKey: normalizedTenant,
    name: name || normalizedEmail,
    role: 'admin',
    createdAt: new Date().toISOString()
  };
  await repository.createUser(user);
  await logAudit('user.register', { email: normalizedEmail, tenantKey: normalizedTenant, repository: repository.mode });
  return issueToken(user);
}

export async function login({ email, password, tenantKey }) {
  const normalizedEmail = String(email || '').trim().toLowerCase();
  const normalizedTenant = String(tenantKey || '').trim().toLowerCase();
  const user = await repository.findUserByEmailTenant(normalizedEmail, normalizedTenant);
  if (!user) throw new Error('Ongeldige gegevens');
  const ok = await bcrypt.compare(password || '', user.passwordHash);
  if (!ok) throw new Error('Ongeldige gegevens');
  await logAudit('user.login', { email: normalizedEmail, tenantKey: normalizedTenant });
  return issueToken(user);
}

export function meFromTokenPayload(payload) {
  return {
    id: payload.sub,
    email: payload.email,
    tenantKey: payload.tenantKey,
    name: payload.name,
    role: payload.role
  };
}

export function verifyToken(token) {
  return jwt.verify(token, env.jwtSecret);
}

export async function createResetToken({ email, tenantKey }) {
  const normalizedEmail = String(email || '').trim().toLowerCase();
  const normalizedTenant = String(tenantKey || '').trim().toLowerCase();
  const user = await repository.findUserByEmailTenant(normalizedEmail, normalizedTenant);
  if (!user) return { accepted: true };
  const token = randomUUID();
  await repository.createPasswordReset({ id: randomUUID(), token, userId: user.id, expiresAt: Date.now() + 1000 * 60 * 30 });
  await logAudit('user.reset.request', { email: user.email, tenantKey: normalizedTenant });
  return env.allowResetTokenInResponse ? { accepted: true, token } : { accepted: true };
}

export async function resetPassword({ token, password }) {
  if (!token || !password || password.length < 8) throw new Error('Reset token of wachtwoord ongeldig');
  const found = await repository.findPasswordReset(token);
  if (!found) throw new Error('Reset token ongeldig of verlopen');
  const passwordHash = await bcrypt.hash(password, 10);
  await repository.updateUserPassword(found.userId, passwordHash);
  await repository.deletePasswordReset(token);
  await logAudit('user.reset.complete', { token });
  return { accepted: true };
}

function issueToken(user) {
  const payload = {
    sub: user.id,
    email: user.email,
    tenantKey: user.tenantKey,
    name: user.name,
    role: user.role
  };
  const token = jwt.sign(payload, env.jwtSecret, { expiresIn: '12h' });
  return { token, user: meFromTokenPayload(payload) };
}
