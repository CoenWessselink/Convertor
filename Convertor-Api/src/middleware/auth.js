import { meFromTokenPayload, verifyToken } from '../services/auth-service.js';

export function requireAuth(req, res, next) {
  const auth = req.headers.authorization || '';
  const [, token] = auth.split(' ');
  if (!token) return res.status(401).json({ error: 'Niet ingelogd' });
  try {
    const payload = verifyToken(token);
    req.user = meFromTokenPayload(payload);
    next();
  } catch {
    return res.status(401).json({ error: 'Token ongeldig' });
  }
}
