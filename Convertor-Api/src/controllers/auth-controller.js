import * as auth from '../services/auth-service.js';

export async function register(req, res, next) {
  try { res.json(await auth.register(req.body)); } catch (e) { next(e); }
}
export async function login(req, res, next) {
  try { res.json(await auth.login(req.body)); } catch (e) { next(e); }
}
export async function requestReset(req, res, next) {
  try { res.json(auth.createResetToken(req.body)); } catch (e) { next(e); }
}
export async function resetPassword(req, res, next) {
  try { res.json(await auth.resetPassword(req.body)); } catch (e) { next(e); }
}
export async function me(req, res) { res.json({ user: req.user }); }
