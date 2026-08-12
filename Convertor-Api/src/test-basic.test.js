import test from 'node:test';
import assert from 'node:assert/strict';
import { detectFormat, parseFile } from './services/parser-service.js';
import { evaluateRules } from './services/rule-engine-service.js';
import { buildViewerPayload, generateDxf } from './services/conversion-service.js';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

function tempFile(name, content) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'convertor-'));
  const filePath = path.join(dir, name);
  fs.writeFileSync(filePath, content, 'utf-8');
  return filePath;
}

test('detecteert STEP', () => {
  assert.equal(detectFormat('part.step', "ISO-10303-21;\nPRODUCT('HEA 200');\nCARTESIAN_POINT('',(0,0,0));"), 'STEP');
});

test('parseert DSTV basisafmetingen', () => {
  const filePath = tempFile('beam.nc1', 'ST\nHEA200\n6000 200 12\nBO 100 100\nAK 1 2');
  const parsed = parseFile(filePath, 'beam.nc1');
  assert.equal(parsed.source.format, 'DSTV');
  assert.equal(parsed.model.dimensions.length, 6000);
  assert.equal(parsed.model.profile, 'HEA200');
});

test('rules engine geeft confidence terug', () => {
  const filePath = tempFile('part.ifc', "ISO-10303-21;\nFILE_SCHEMA(('IFC4'));\n#1=IFCBEAM('x');\n#2=IFCCARTESIANPOINT((0.,0.,0.));\n#3=IFCCARTESIANPOINT((1000.,0.,0.));");
  const parsed = parseFile(filePath, 'part.ifc');
  const analysis = evaluateRules(parsed);
  assert.equal(typeof analysis.confidence, 'number');
  assert.ok(analysis.confidence > 0);
});

test('viewer payload bevat projecties en issue markers', () => {
  const filePath = tempFile('beam.nc1', 'ST\nHEA200\n6000 200 0\nBO 100 100\nAK 1 2');
  const parsed = parseFile(filePath, 'beam.nc1');
  const analysis = evaluateRules(parsed);
  const viewer = buildViewerPayload({ model: parsed.model, analysis });
  assert.ok(viewer.projections.top.segments.length > 0);
  assert.ok(Array.isArray(viewer.projections.front.issueMarkers));
});

test('maakt DXF met layers, lines en issue text', () => {
  const viewer = {
    projections: {
      top: {
        label: 'Bovenaanzicht',
        axes: { horizontal: 'X', vertical: 'Y' },
        width: 100,
        height: 50,
        bounds: { minX: 0, minY: 0, maxX: 100, maxY: 50, width: 100, height: 50 },
        segments: [{ id: 'a', from: { x: 0, y: 0 }, to: { x: 10, y: 0 } }],
        issueMarkers: [{ id: 'i1', code: 'TEST', message: 'melding', position: { x: 5, y: 5 } }]
      },
      front: {
        label: 'Vooraanzicht',
        axes: { horizontal: 'X', vertical: 'Z' },
        width: 100,
        height: 20,
        bounds: { minX: 0, minY: 0, maxX: 100, maxY: 20, width: 100, height: 20 },
        segments: [],
        issueMarkers: []
      },
      side: {
        label: 'Zijaanzicht',
        axes: { horizontal: 'Y', vertical: 'Z' },
        width: 50,
        height: 20,
        bounds: { minX: 0, minY: 0, maxX: 50, maxY: 20, width: 50, height: 20 },
        segments: [],
        issueMarkers: []
      }
    }
  };

  const dxf = generateDxf(viewer);
  assert.match(dxf, /LAYER/);
  assert.match(dxf, /LINE/);
  assert.match(dxf, /TEXT/);
  assert.match(dxf, /TOP_GEOM/);
});
