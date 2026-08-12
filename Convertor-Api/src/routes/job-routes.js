import { Router } from 'express';
import * as ctrl from '../controllers/job-controller.js';
import { requireAuth } from '../middleware/auth.js';
import { upload } from '../services/upload-service.js';
import { requireFiles, validateBody } from '../middleware/validation.js';

const router = Router();
router.use(requireAuth);
router.post('/upload', upload.array('files', 20), requireFiles(), ctrl.uploadAndAnalyze);
router.post('/demo-sample', validateBody({ sampleKey: { required: false, type: 'string', minLength: 2 } }), ctrl.createDemo);
router.get('/', ctrl.jobs);
router.get('/:jobId', ctrl.jobDetail);
router.post('/:jobId/retry', ctrl.retry);
router.get('/:jobId/viewer', ctrl.viewer);
router.get('/:jobId/dxf', ctrl.dxf);
export default router;
