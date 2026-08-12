import bcrypt from 'bcryptjs';
import { randomUUID } from 'node:crypto';
import { repository } from '../src/repositories/index.js';

const email = process.env.SEED_EMAIL || 'admin@demo.com';
const password = process.env.SEED_PASSWORD || 'Admin123!';
const tenantKey = process.env.SEED_TENANT || 'demo';

await repository.init();
const existing = await repository.findUserByEmailTenant(email.toLowerCase(), tenantKey.toLowerCase());
if (existing) {
  console.log('Seed gebruiker bestaat al');
  process.exit(0);
}
const passwordHash = await bcrypt.hash(password, 10);
await repository.createUser({
  id: randomUUID(),
  email: email.toLowerCase(),
  passwordHash,
  tenantKey: tenantKey.toLowerCase(),
  name: 'Demo Admin',
  role: 'admin',
  createdAt: new Date().toISOString()
});
console.log('Seed gebruiker aangemaakt:', email, tenantKey);
