import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

export const supportedModelExtensions = new Set(['.step', '.stp', '.ifc', '.nc', '.nc1']);

export const modelRoots = [
  { kind: 'repository', relativePath: 'reference-models', optional: false, confidential: false },
  { kind: 'local', relativePath: 'reference-models-local', optional: true, confidential: true }
].map((root) => ({ ...root, absolutePath: repoPath(root.relativePath) }));

export const resultRoots = [
  { kind: 'repository', relativePath: 'reference-results', optional: false },
  { kind: 'local', relativePath: 'reference-results-local', optional: true }
].map((root) => ({ ...root, absolutePath: repoPath(root.relativePath) }));

export function repoPath(relativePath) {
  return path.resolve(repoRoot, fromPosixPath(relativePath));
}

export function repoRelative(absolutePath) {
  return toPosixPath(path.relative(repoRoot, absolutePath));
}

export function toPosixPath(value) {
  return String(value).split(path.sep).join('/');
}

export function fromPosixPath(value) {
  return String(value).split('/').join(path.sep);
}

export function ensureDirectory(directoryPath) {
  fs.mkdirSync(directoryPath, { recursive: true });
}

export function writeJson(filePath, value) {
  ensureDirectory(path.dirname(filePath));
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf-8');
}

export function discoverReferenceModels() {
  const models = [];

  for (const root of modelRoots) {
    if (!fs.existsSync(root.absolutePath)) continue;

    for (const absolutePath of walk(root.absolutePath, isSupportedModelFile)) {
      const relativePath = repoRelative(absolutePath);
      models.push({
        id: modelIdFromRelativePath(relativePath),
        absolutePath,
        relativePath,
        format: inferFormatFromPath(absolutePath),
        sourceKind: root.kind,
        confidential: root.confidential
      });
    }
  }

  return models.sort((a, b) => a.relativePath.localeCompare(b.relativePath));
}

export function discoverExpectationFiles() {
  const files = [];

  for (const root of resultRoots) {
    if (!fs.existsSync(root.absolutePath)) continue;
    files.push(...walk(root.absolutePath, (filePath) => filePath.endsWith('.expected.json')));
  }

  return files.sort((a, b) => a.localeCompare(b));
}

export function loadExpectations() {
  return discoverExpectationFiles().flatMap((filePath) => {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    const records = Array.isArray(parsed.models) ? parsed.models : [parsed];
    return records.map((record) => ({ ...record, __file: repoRelative(filePath) }));
  });
}

export function expectationRelativePathForModel(model) {
  const root = model.confidential ? 'reference-results-local' : 'reference-results';
  return `${root}/${model.format}/${model.id}.expected.json`;
}

export function inferFormatFromPath(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  if (extension === '.step' || extension === '.stp') return 'STEP';
  if (extension === '.ifc') return 'IFC';
  if (extension === '.nc' || extension === '.nc1') return 'DSTV';
  return 'UNKNOWN';
}

export function modelIdFromRelativePath(relativePath) {
  return relativePath
    .replace(/^reference-models-local\//, 'local/')
    .replace(/^reference-models\//, 'repo/')
    .replace(/\.[^.]+$/, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function valueAtPath(value, propertyPath) {
  const segments = [...String(propertyPath).matchAll(/([^.[\]]+)|\[(\d+)\]/g)]
    .map((match) => match[1] ?? Number(match[2]));

  return segments.reduce((current, segment) => {
    if (current == null) return undefined;
    return current[segment];
  }, value);
}

export function formatValue(value) {
  if (value === undefined) return '<undefined>';
  return JSON.stringify(value);
}

function isSupportedModelFile(filePath) {
  return supportedModelExtensions.has(path.extname(filePath).toLowerCase());
}

function walk(root, predicate) {
  const files = [];
  const entries = fs.readdirSync(root, { withFileTypes: true });

  for (const entry of entries) {
    if (entry.name.startsWith('.')) continue;

    const absolutePath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(absolutePath, predicate));
    } else if (entry.isFile() && predicate(absolutePath)) {
      files.push(absolutePath);
    }
  }

  return files;
}
