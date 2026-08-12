import { Router } from 'express';
import * as ctrl from '../controllers/auth-controller.js';
import { requireAuth } from '../middleware/auth.js';
import { validateBody } from '../middleware/validation.js';
import { authRateLimit } from '../middleware/rate-limit.js';

const router = Router();
router.post('/register', authRateLimit(), validateBody({ email: { required: true, type: 'string', minLength: 3 }, password: { required: true, type: 'string', minLength: 8 }, tenantKey: { required: true, type: 'string', minLength: 2 } }), ctrl.register);
router.post('/login', authRateLimit(), validateBody({ email: { required: true, type: 'string', minLength: 3 }, password: { required: true, type: 'string', minLength: 1 }, tenantKey: { required: true, type: 'string', minLength: 2 } }), ctrl.login);
router.post('/request-reset', authRateLimit(), validateBody({ email: { required: true, type: 'string', minLength: 3 }, tenantKey: { required: true, type: 'string', minLength: 2 } }), ctrl.requestReset);
router.post('/reset-password', authRateLimit(), validateBody({ token: { required: true, type: 'string', minLength: 3 }, password: { required: true, type: 'string', minLength: 8 } }), ctrl.resetPassword);
router.get('/me', requireAuth, ctrl.me);
export default router;
