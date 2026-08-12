import { randomUUID } from 'node:crypto';
import path from 'node:path';
import fs from 'node:fs';
import { parseFile } from './parser-service.js';
import { evaluateRules } from './rule-engine-service.js';
import { buildViewerPayload, generateDxf } from './conversion-service.js';
import { env } from '../config/env.js';
import { logAudit } from './audit-service.js';
import { repository } from '../repositories/index.js';

const resultsDir = path.join(env.dataDir, 'results');
fs.mkdirSync(resultsDir, { recursive: true });

const demoSamples = {
  step: {
    filename: 'demo-balk.step',
    content: `ISO-10303-21;
HEADER;
ENDSEC;
DATA;
PRODUCT('HEA 200');
CARTESIAN_POINT('',(0,0,0));
CARTESIAN_POINT('',(6000,0,0));
CARTESIAN_POINT('',(6000,200,0));
CARTESIAN_POINT('',(0,200,0));
CARTESIAN_POINT('',(0,0,300));
CARTESIAN_POINT('',(6000,0,300));
CARTESIAN_POINT('',(6000,200,300));
CARTESIAN_POINT('',(0,200,300));
ADVANCED_FACE('',(),$, .T.);
ENDSEC;
END-ISO-10303-21;`
  },
  ifc: {
    filename: 'demo-frame.ifc',
    content: `ISO-10303-21;
HEADER;
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCBEAM('beam-1');
#2=IFCCARTESIANPOINT((0.,0.,0.));
#3=IFCCARTESIANPOINT((4200.,0.,0.));
#4=IFCCARTESIANPOINT((4200.,250.,0.));
#5=IFCCARTESIANPOINT((0.,250.,0.));
#6=IFCCARTESIANPOINT((0.,0.,450.));
#7=IFCCARTESIANPOINT((4200.,0.,450.));
#8=IFCCARTESIANPOINT((4200.,250.,450.));
#9=IFCCARTESIANPOINT((0.,250.,450.));
ENDSEC;
END-ISO-10303-21;`
  },
  nc1: {
    filename: 'demo-profiel.nc1',
    content: `ST
HEA200
6000 200 300
BO 100 100
AK 1 2`
  }
};

export async function createJobsFromUploads(files, user) {
  const created = [];
  for (const f of files) {
    const createdJob = await persistJobFromFile({
      tenantKey: user.tenantKey,
      path: f.path,
      originalname: f.originalname,
      size: f.size
    });
    created.push(createdJob);
  }
  await logAudit('jobs.create', { count: created.length, tenantKey: user.tenantKey });
  return created;
}

export async function createDemoSampleJob(user, sampleKey = 'step') {
  const sample = demoSamples[sampleKey] || demoSamples.step;
  const safeName = `${Date.now()}-${sample.filename}`;
  const filePath = path.join(env.uploadsDir, safeName);
  fs.writeFileSync(filePath, sample.content, 'utf-8');

  const created = await persistJobFromFile({
    tenantKey: user.tenantKey,
    path: filePath,
    originalname: sample.filename,
    size: Buffer.byteLength(sample.content, 'utf-8')
  });

  await processJob(created.jobId, user.tenantKey);
  await logAudit('jobs.demoSample', { tenantKey: user.tenantKey, sampleKey, filename: sample.filename });
  return getJob(created.jobId, user.tenantKey);
}

async function persistJobFromFile({ tenantKey, path: filePath, originalname, size }) {
  const fileId = randomUUID();
  const jobId = randomUUID();
  const now = new Date().toISOString();
  await repository.createFile({ id: fileId, tenantKey, path: filePath, originalname, size, createdAt: now });
  await repository.createJob({ id: jobId, fileId, tenantKey, status: 'pending', error: null, createdAt: now, updatedAt: now });
  return { jobId, fileId, originalname };
}

export async function processJob(jobId, tenantKey) {
  const job = await repository.findJob(jobId, tenantKey);
  if (!job) throw new Error('Job niet gevonden');
  await repository.updateJob(jobId, tenantKey, { status: 'processing', updatedAt: new Date().toISOString(), error: null });

  try {
    const file = await repository.findFile(job.fileId, tenantKey);
    if (!file) throw new Error('Bronbestand niet gevonden');
    const parsed = parseFile(file.path, file.originalname);
    const analysis = evaluateRules(parsed);
    const result = {
      source: parsed.source,
      model: parsed.model,
      metrics: parsed.metrics,
      findings: parsed.findings,
      analysis
    };
    const viewer = buildViewerPayload(result);
    const dxf = generateDxf(viewer);
    const resultId = randomUUID();
    const dxfFile = path.join(resultsDir, `${resultId}.dxf`);
    fs.writeFileSync(dxfFile, dxf, 'utf-8');

    await repository.createResult({
      id: resultId,
      jobId: job.id,
      tenantKey,
      format: parsed.source.format,
      source: parsed.source,
      model: parsed.model,
      metrics: parsed.metrics,
      findings: parsed.findings,
      analysis,
      viewer,
      confidence: analysis.confidence,
      dxfPath: dxfFile,
      createdAt: new Date().toISOString()
    });
    await repository.updateJob(job.id, tenantKey, { status: 'done', updatedAt: new Date().toISOString(), error: null });
    await logAudit('jobs.processed', { jobId, tenantKey, confidence: analysis.confidence, format: parsed.source.format });
  } catch (err) {
    await repository.updateJob(jobId, tenantKey, { status: 'failed', error: err.message, updatedAt: new Date().toISOString() });
    await logAudit('jobs.failed', { jobId, tenantKey, error: err.message });
    throw err;
  }
}

export async function retryJob(jobId, tenantKey) {
  await repository.updateJob(jobId, tenantKey, { status: 'pending', error: null, updatedAt: new Date().toISOString() });
  return processJob(jobId, tenantKey);
}

export async function listJobs(tenantKey) {
  const jobs = await repository.listJobs(tenantKey);
  const enriched = [];
  for (const job of jobs) {
    const file = await repository.findFile(job.fileId, tenantKey);
    const result = await repository.findResultByJob(job.id, tenantKey);
    enriched.push({
      ...job,
      filename: file?.originalname,
      resultId: result?.id,
      format: result?.format,
      confidence: result?.confidence,
      profile: result?.model?.profile,
      dimensions: result?.model?.dimensions,
      issueCount: result?.analysis?.summary?.issueCount || 0,
      warningCount: result?.analysis?.summary?.warningCount || 0,
      preview: result?.viewer?.projections?.top?.label || null
    });
  }
  return enriched;
}

export async function getJob(jobId, tenantKey) {
  const job = await repository.findJob(jobId, tenantKey);
  if (!job) throw new Error('Job niet gevonden');
  const file = await repository.findFile(job.fileId, tenantKey);
  const result = await repository.findResultByJob(job.id, tenantKey);
  return { ...job, filename: file?.originalname, result };
}

export async function getViewer(jobId, tenantKey) {
  const job = await getJob(jobId, tenantKey);
  if (!job.result) throw new Error('Nog geen resultaat');
  return job.result.viewer;
}

export async function getDxfPath(jobId, tenantKey) {
  const job = await getJob(jobId, tenantKey);
  if (!job.result?.dxfPath) throw new Error('DXF niet beschikbaar');
  return job.result.dxfPath;
}
