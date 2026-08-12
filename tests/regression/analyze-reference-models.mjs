import path from 'node:path';
import { performance } from 'node:perf_hooks';
import { parseFile } from '../../Convertor-Api/src/services/parser-service.js';
import { evaluateRules } from '../../Convertor-Api/src/services/rule-engine-service.js';
import { buildViewerPayload } from '../../Convertor-Api/src/services/conversion-service.js';
import {
  discoverReferenceModels,
  expectationRelativePathForModel,
  loadExpectations,
  repoPath,
  writeJson
} from './reference-utils.mjs';

const write = process.argv.includes('--write');
const overwrite = process.argv.includes('--overwrite');

const models = discoverReferenceModels();
const expectationsByModelPath = new Map(loadExpectations().map((expectation) => [expectation.model.path, expectation]));

if (models.length === 0) {
  console.log('Geen referentiemodellen gevonden in reference-models/ of reference-models-local/.');
  process.exit(0);
}

let created = 0;
let skipped = 0;

for (const model of models) {
  const existing = expectationsByModelPath.get(model.relativePath);
  if (existing && !overwrite) {
    console.log(`Bestaat al: ${existing.__file} voor ${model.relativePath}`);
    skipped += 1;
    continue;
  }

  const draft = analyzeReferenceModel(model);
  const outputRelativePath = expectationRelativePathForModel(model);
  const outputPath = repoPath(outputRelativePath);

  if (write) {
    writeJson(outputPath, draft);
    console.log(`${existing ? 'Overschreven' : 'Aangemaakt'}: ${outputRelativePath}`);
    created += 1;
  } else {
    console.log(`\n${model.relativePath}`);
    console.log(JSON.stringify(draft, null, 2));
  }
}

if (!write) {
  console.log('\nGebruik `npm run reference:analyze -- --write` om ontbrekende draft expected-results aan te maken.');
} else {
  console.log(`\nKlaar. Aangemaakt/overschreven: ${created}. Overgeslagen: ${skipped}.`);
  console.log('Controleer de bestanden handmatig en zet validation.status pas op validated als de waarden betrouwbaar zijn.');
}

function analyzeReferenceModel(model) {
  const startHeap = process.memoryUsage().heapUsed;
  const start = performance.now();
  const parsed = parseFile(model.absolutePath, path.basename(model.absolutePath));
  const parseMs = performance.now() - start;
  const analysis = evaluateRules(parsed);
  const viewer = buildViewerPayload({ model: parsed.model, analysis });
  const totalMs = performance.now() - start;
  const heapDeltaMb = (process.memoryUsage().heapUsed - startHeap) / 1024 / 1024;

  return buildDraftExpectation(model, parsed, analysis, viewer, {
    parseMs: round2(parseMs),
    totalMs: round2(totalMs),
    heapDeltaMb: round2(heapDeltaMb)
  });
}

function buildDraftExpectation(model, parsed, analysis, viewer, observedPerformance) {
  return {
    schemaVersion: 1,
    model: {
      id: model.id,
      path: model.relativePath,
      format: parsed.source.format,
      confidential: model.confidential
    },
    validation: {
      status: 'manual_validation_required',
      validatedBy: '',
      validatedAt: '',
      notes: 'Draft gegenereerd uit parseroutput. Controleer tegen gevalideerde brondata voordat deze baseline op validated wordt gezet.'
    },
    comparison: {
      exact: compactObject({
        'source.format': parsed.source.format,
        'model.profile': parsed.model.profile,
        'model.entities': parsed.model.entities,
        'model.operations': parsed.model.operations,
        'analysis.summary': analysis.summary,
        'viewer.summary.issueCount': viewer.summary.issueCount,
        'viewer.summary.projectionModes': viewer.summary.projectionModes
      }),
      tolerance: numericToleranceEntries({
        'model.dimensions.length': parsed.model.dimensions?.length,
        'model.dimensions.width': parsed.model.dimensions?.width,
        'model.dimensions.height': parsed.model.dimensions?.height,
        'metrics.volume': parsed.metrics?.volume,
        'metrics.weight': parsed.metrics?.weight,
        'metrics.surfaceArea': parsed.metrics?.surfaceArea,
        'analysis.confidence': analysis.confidence
      }),
      metadata: {
        'source.filename': {
          comparison: 'informational',
          observed: parsed.source.filename,
          note: 'Bestandsnaam kan per export of lokale opslag verschillen.'
        },
        'source.sizeBytes': {
          comparison: 'informational',
          observed: parsed.source.sizeBytes
        },
        'source.lineCount': {
          comparison: 'informational',
          observed: parsed.source.lineCount
        },
        'model.metadata': {
          comparison: 'informational',
          observed: parsed.model.metadata
        },
        findings: {
          comparison: 'informational',
          observed: parsed.findings
        }
      },
      performance: {
        maxParseMs: Math.max(1000, Math.ceil(observedPerformance.parseMs * 5)),
        maxTotalMs: Math.max(1500, Math.ceil(observedPerformance.totalMs * 5)),
        maxHeapDeltaMb: Math.max(128, Math.ceil(Math.max(0, observedPerformance.heapDeltaMb) * 5))
      }
    },
    observed: {
      parser: parsed,
      analysis,
      viewerSummary: viewer.summary,
      performance: observedPerformance
    }
  };
}

function numericToleranceEntries(values) {
  return Object.fromEntries(
    Object.entries(values)
      .filter(([, value]) => typeof value === 'number' && Number.isFinite(value))
      .map(([property, value]) => [
        property,
        {
          expected: value,
          tolerance: property === 'analysis.confidence' ? 0.01 : 0.001,
          unit: unitForProperty(property)
        }
      ])
  );
}

function compactObject(value) {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined && item !== null)
  );
}

function unitForProperty(property) {
  if (property.includes('dimensions')) return 'mm';
  if (property.includes('volume')) return 'mm3';
  if (property.includes('weight')) return 'kg';
  if (property.includes('surfaceArea')) return 'mm2';
  return '';
}

function round2(value) {
  return Number(value.toFixed(2));
}
