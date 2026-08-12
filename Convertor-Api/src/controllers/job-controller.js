import fs from 'node:fs';
import { createJobsFromUploads, processJob, retryJob, listJobs, getJob, getViewer, getDxfPath, createDemoSampleJob } from '../services/job-service.js';

export async function uploadAndAnalyze(req, res, next) {
  try {
    const jobs = await createJobsFromUploads(req.files || [], req.user);
    for (const job of jobs) {
      await processJob(job.jobId, req.user.tenantKey);
    }
    res.json({ jobs });
  } catch (e) { next(e); }
}

export async function createDemo(req, res, next) {
  try {
    res.json(await createDemoSampleJob(req.user, req.body?.sampleKey));
  } catch (e) { next(e); }
}

export async function jobs(req, res, next) {
  try { res.json({ jobs: await listJobs(req.user.tenantKey) }); } catch (e) { next(e); }
}
export async function jobDetail(req, res, next) {
  try { res.json(await getJob(req.params.jobId, req.user.tenantKey)); } catch (e) { next(e); }
}
export async function viewer(req, res, next) {
  try { res.json(await getViewer(req.params.jobId, req.user.tenantKey)); } catch (e) { next(e); }
}
export async function dxf(req, res, next) {
  try {
    const dxfPath = await getDxfPath(req.params.jobId, req.user.tenantKey);
    res.setHeader('Content-Type', 'application/dxf');
    res.setHeader('Content-Disposition', `attachment; filename="${req.params.jobId}.dxf"`);
    fs.createReadStream(dxfPath).pipe(res);
  } catch (e) { next(e); }
}
export async function retry(req, res, next) {
  try {
    await retryJob(req.params.jobId, req.user.tenantKey);
    res.json({ accepted: true });
  } catch (e) { next(e); }
}
