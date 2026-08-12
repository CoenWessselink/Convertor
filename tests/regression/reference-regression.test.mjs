import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { performance } from 'node:perf_hooks';
import { parseFile } from '../../Convertor-Api/src/services/parser-service.js';
import { evaluateRules } from '../../Convertor-Api/src/services/rule-engine-service.js';
import { buildViewerPayload } from '../../Convertor-Api/src/services/conversion-service.js';
import {
  discoverReferenceModels,
  formatValue,
  loadExpectations,
  modelRoots,
  repoPath,
  resultRoots,
  valueAtPath
} from './reference-utils.mjs';

const models = discoverReferenceModels();
const expectations = loadExpectations();

test('reference mappen bestaan', () => {
  for (const root of modelRoots.filter((item) => !item.optional)) {
    assert.ok(fs.existsSync(root.absolutePath), `${root.relativePath} ontbreekt`);
  }

  for (const root of resultRoots.filter((item) => !item.optional)) {
    assert.ok(fs.existsSync(root.absolutePath), `${root.relativePath} ontbreekt`);
  }
});

test('expected-result schema is geldig', () => {
  const seenModelPaths = new Set();

  for (const expectation of expectations) {
    validateExpectation(expectation);

    const modelPath = expectation.model.path;
    assert.ok(
      !seenModelPaths.has(modelPath),
      `${expectation.__file}: dubbel expected-result voor ${modelPath}`
    );
    seenModelPaths.add(modelPath);
  }
});

test('ieder referentiemodel heeft een expected-result bestand', () => {
  const expectedByModelPath = new Set(expectations.map((item) => item.model?.path));
  const missing = models
    .filter((model) => !expectedByModelPath.has(model.relativePath))
    .map((model) => `${model.relativePath} -> ${model.format}`);

  assert.equal(
    missing.length,
    0,
    [
      'Een of meer referentiemodellen missen een expected-result bestand.',
      'Run `npm run reference:analyze -- --write` en valideer de uitkomsten handmatig.',
      `Ontbrekend: ${missing.join(', ')}`
    ].join('\n')
  );
});

test('ieder expected-result verwijst naar een bestaand model', () => {
  const modelPaths = new Set(models.map((model) => model.relativePath));
  const missing = expectations
    .filter((expectation) => !modelPaths.has(expectation.model?.path))
    .map((expectation) => `${expectation.__file} -> ${expectation.model?.path || '<geen path>'}`);

  assert.equal(
    missing.length,
    0,
    [
      'Een of meer expected-results verwijzen naar een ontbrekend referentiemodel.',
      'Controleer of het model bewust is verwijderd en update pas daarna de baseline.',
      `Ontbrekend: ${missing.join(', ')}`
    ].join('\n')
  );
});

for (const expectation of expectations) {
  const name = `reference baseline: ${expectation.model?.path || expectation.__file}`;
  const status = expectation.validation?.status;

  test(name, status === 'manual_validation_required' ? { skip: 'manual validation required' } : {}, () => {
    assert.equal(
      status,
      'validated',
      `${expectation.__file}: validation.status moet validated zijn voordat regressiewaarden worden vergeleken`
    );

    const modelPath = repoPath(expectation.model.path);
    assert.ok(fs.existsSync(modelPath), `${expectation.model.path} bestaat niet`);

    const actual = analyzeModel(modelPath);
    compareExact(expectation, actual);
    compareTolerance(expectation, actual);
    compareMetadata(expectation, actual);
    comparePerformance(expectation, actual);
  });
}

function analyzeModel(modelPath) {
  const startHeap = process.memoryUsage().heapUsed;
  const start = performance.now();
  const parsed = parseFile(modelPath, path.basename(modelPath));
  const parseMs = performance.now() - start;
  const analysis = evaluateRules(parsed);
  const viewer = buildViewerPayload({ model: parsed.model, analysis });
  const totalMs = performance.now() - start;
  const heapDeltaMb = (process.memoryUsage().heapUsed - startHeap) / 1024 / 1024;

  return {
    ...parsed,
    analysis,
    viewer,
    performance: {
      parseMs: round2(parseMs),
      totalMs: round2(totalMs),
      heapDeltaMb: round2(heapDeltaMb)
    }
  };
}

function validateExpectation(expectation) {
  assert.equal(expectation.schemaVersion, 1, `${expectation.__file}: schemaVersion moet 1 zijn`);
  assert.ok(expectation.model?.id, `${expectation.__file}: model.id ontbreekt`);
  assert.ok(expectation.model?.path, `${expectation.__file}: model.path ontbreekt`);
  assert.ok(!expectation.model.path.includes('\\'), `${expectation.__file}: gebruik forward slashes in model.path`);
  assert.ok(['STEP', 'IFC', 'DSTV'].includes(expectation.model?.format), `${expectation.__file}: onbekend model.format`);
  assert.equal(typeof expectation.model.confidential, 'boolean', `${expectation.__file}: model.confidential moet boolean zijn`);
  assert.ok(
    ['validated', 'manual_validation_required'].includes(expectation.validation?.status),
    `${expectation.__file}: validation.status moet validated of manual_validation_required zijn`
  );
  assert.equal(typeof expectation.comparison, 'object', `${expectation.__file}: comparison ontbreekt`);
}

function compareExact(expectation, actual) {
  for (const [property, expected] of Object.entries(expectation.comparison.exact || {})) {
    const found = valueAtPath(actual, property);
    assert.deepEqual(
      found,
      expected,
      regressionMessage(expectation, property, expected, found, 'Exacte golden value verschilt van de huidige analyse.')
    );
  }
}

function compareTolerance(expectation, actual) {
  for (const [property, rule] of Object.entries(expectation.comparison.tolerance || {})) {
    const expected = rule.expected;
    const tolerance = rule.tolerance ?? 0;
    const found = valueAtPath(actual, property);

    assert.equal(
      typeof found,
      'number',
      regressionMessage(expectation, property, expected, found, 'Numerieke waarde ontbreekt of is geen getal.')
    );

    const difference = Math.abs(found - expected);
    assert.ok(
      difference <= tolerance,
      regressionMessage(
        expectation,
        property,
        `${expected} +/- ${tolerance}${rule.unit ? ` ${rule.unit}` : ''}`,
        found,
        `Verschil ${difference} is groter dan toegestane tolerantie.`
      )
    );
  }
}

function compareMetadata(expectation, actual) {
  for (const [property, rule] of Object.entries(expectation.comparison.metadata || {})) {
    if (!rule || rule.comparison === 'informational') continue;

    const found = valueAtPath(actual, property);
    if (rule.comparison === 'exact') {
      assert.deepEqual(
        found,
        rule.expected,
        regressionMessage(expectation, property, rule.expected, found, 'Metadata staat op exacte vergelijking en wijkt af.')
      );
    }

    if (rule.comparison === 'pattern') {
      assert.match(
        String(found ?? ''),
        new RegExp(rule.pattern),
        regressionMessage(expectation, property, rule.pattern, found, 'Metadata voldoet niet aan het verwachte patroon.')
      );
    }
  }
}

function comparePerformance(expectation, actual) {
  const performanceRules = expectation.comparison.performance || {};

  comparePerformanceLimit(expectation, 'performance.parseMs', performanceRules.maxParseMs, actual.performance.parseMs);
  comparePerformanceLimit(expectation, 'performance.totalMs', performanceRules.maxTotalMs, actual.performance.totalMs);
  comparePerformanceLimit(expectation, 'performance.heapDeltaMb', performanceRules.maxHeapDeltaMb, actual.performance.heapDeltaMb);
}

function comparePerformanceLimit(expectation, property, maxValue, found) {
  if (maxValue == null) return;

  assert.ok(
    found <= maxValue,
    regressionMessage(expectation, property, `<= ${maxValue}`, found, 'Performancegrens is overschreden.')
  );
}

function regressionMessage(expectation, property, expected, found, cause) {
  return [
    `Model: ${expectation.model.path}`,
    `Eigenschap: ${property}`,
    `Verwachte waarde: ${formatValue(expected)}`,
    `Gevonden waarde: ${formatValue(found)}`,
    `Vermoedelijke oorzaak: ${cause}`,
    `Baseline: ${expectation.__file}`
  ].join('\n');
}

function round2(value) {
  return Number(value.toFixed(2));
}
