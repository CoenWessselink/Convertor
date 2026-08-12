import fs from 'node:fs';

export function detectFormat(filename, content) {
  const lower = filename.toLowerCase();
  if (lower.endsWith('.ifc') || (/ISO-10303-21/i.test(content) && /FILE_SCHEMA\(\('IFC/i.test(content))) return 'IFC';
  if (lower.endsWith('.stp') || lower.endsWith('.step') || /ISO-10303-21/i.test(content)) return 'STEP';
  if (lower.endsWith('.nc') || lower.endsWith('.nc1') || /^ST\b/m.test(content) || /^(AK|BO|SI|PU)\b/m.test(content)) return 'DSTV';
  return 'UNKNOWN';
}

export function parseFile(filePath, originalname) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const format = detectFormat(originalname, content);
  const parsed = format === 'STEP'
    ? parseStep(content, originalname)
    : format === 'DSTV'
      ? parseDstv(content, originalname)
      : format === 'IFC'
        ? parseIfc(content, originalname)
        : parseUnknown(content, originalname);

  return normalizeParsedResult(parsed, content, originalname, format);
}

function normalizeParsedResult(parsed, content, filename, format) {
  const bbox = parsed.geometry.bbox;
  const dimensions = {
    length: round2(bbox.width),
    width: round2(bbox.depth),
    height: round2(bbox.height)
  };

  return {
    source: {
      filename,
      format,
      sizeBytes: Buffer.byteLength(content, 'utf-8'),
      lineCount: content.split(/\r?\n/).length
    },
    model: {
      format,
      profile: parsed.profile,
      dimensions,
      geometry: parsed.geometry,
      entities: parsed.entities,
      operations: parsed.operations,
      metadata: parsed.metadata
    },
    metrics: {
      ...parsed.metrics,
      dimensions
    },
    findings: parsed.findings
  };
}

function parseStep(content, filename) {
  const lines = content.split(/\r?\n/);
  const cartesian = [...content.matchAll(/CARTESIAN_POINT\s*\([^()]*\(([-0-9.E+]+)\s*,\s*([-0-9.E+]+)\s*,\s*([-0-9.E+]+)\)\)/gi)]
    .map((m) => ({ x: num(m[1]), y: num(m[2]), z: num(m[3]) }));
  const faces = count(content, /ADVANCED_FACE/gi);
  const edges = count(content, /EDGE_CURVE/gi);
  const solids = count(content, /MANIFOLD_SOLID_BREP|SHELL_BASED_SURFACE_MODEL/gi);
  const productName = firstMatch(content, /PRODUCT\('([^']+)'/i) || filename;
  const geometry = cartesian.length ? geometryFromPoints(cartesian, filename) : fallbackGeometry(filename);

  return {
    profile: guessProfile(productName, content),
    metadata: { productName },
    entities: { cartesianPoints: cartesian.length, faces, edges, solids },
    operations: [],
    metrics: { lines: lines.length, points: cartesian.length, faces, edges, solids },
    findings: [
      `STEP-product: ${productName}`,
      `${faces} faces en ${edges} edges gevonden.`,
      cartesian.length ? 'Geometrie afgeleid uit CARTESIAN_POINT.' : 'Geen CARTESIAN_POINT gevonden; bbox-fallback toegepast.'
    ],
    geometry
  };
}

function parseDstv(content, filename) {
  const lines = content.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const holeCount = lines.filter((l) => /^BO\b/.test(l)).length;
  const cutCount = lines.filter((l) => /^(AK|SI|PU)\b/.test(l)).length;
  const profile = (firstMatch(content, /\b(HEA\s?\d{2,4}|HEB\s?\d{2,4}|HEM\s?\d{2,4}|IPE\s?\d{2,4}|IPN\s?\d{2,4}|UNP\s?\d{2,4}|UPE\s?\d{2,4}|L\s?\d+x\d+x\d+)\b/i)?.replace(/\s+/g, '') || 'ONBEKEND');
  const dimensionNumbers = [...content.matchAll(/\b(\d{2,6})\b/g)].map((m) => Number(m[1]));
  const length = dimensionNumbers.find((n) => n >= 500 && n <= 50000) || 6000;
  const width = dimensionNumbers.find((n) => n >= 40 && n <= 2000 && n !== length) || 220;
  const height = dimensionNumbers.find((n) => n >= 4 && n <= 300 && n !== length && n !== width) || 12;
  const geometry = geometryFromPrism(length, width, height, filename);

  return {
    profile,
    metadata: { profile },
    entities: { headerLines: Math.min(5, lines.length), operationLines: holeCount + cutCount },
    operations: [
      { type: 'holes', count: holeCount },
      { type: 'cuts', count: cutCount }
    ],
    metrics: { lines: lines.length, holes: holeCount, cuts: cutCount, length, width, height },
    findings: [
      `Profielherkenning: ${profile}`,
      `${holeCount} boorregels en ${cutCount} contourregels gevonden.`
    ],
    geometry
  };
}

function parseIfc(content, filename) {
  const entities = [...content.matchAll(/#\d+\s*=\s*([A-Z0-9_]+)/g)].map((m) => m[1]);
  const productTypes = summarize(entities.filter((e) => e.startsWith('IFC')));
  const points = [...content.matchAll(/IFCCARTESIANPOINT\s*\(\(([-0-9.E+]+),\s*([-0-9.E+]+)(?:,\s*([-0-9.E+]+))?\)\)/gi)]
    .map((m) => ({ x: num(m[1]), y: num(m[2]), z: num(m[3] || '0') }));
  const beams = count(content, /IFCBEAM/gi);
  const columns = count(content, /IFCCOLUMN/gi);
  const profile = firstMatch(content, /IFC(?:I|L|U|C|T|Z)SHAPEPROFILEDEF\('([^']+)'/i) || guessProfile(filename, content);
  const geometry = points.length ? geometryFromPoints(points, filename) : fallbackGeometry(filename);

  return {
    profile,
    metadata: { dominantEntities: productTypes.slice(0, 8) },
    entities: { total: entities.length, beams, columns, cartesianPoints: points.length },
    operations: [],
    metrics: { entities: entities.length, beams, columns, points: points.length },
    findings: [
      `${entities.length} IFC-entiteiten gevonden.`,
      beams || columns ? `Objecten: ${beams} beam(s), ${columns} column(s).` : 'Geen IFCBEAM/IFCCOLUMN entity gevonden.',
      profile ? `Profielindicatie: ${profile}` : 'Geen profielnaam uit IFC kunnen afleiden.'
    ],
    geometry
  };
}

function parseUnknown(content, filename) {
  return {
    profile: 'ONBEKEND',
    metadata: {},
    entities: {},
    operations: [],
    metrics: { lines: content.split(/\r?\n/).length },
    findings: ['Bestandstype niet herkend.'],
    geometry: fallbackGeometry(filename)
  };
}

function geometryFromPrism(length, width, height, label) {
  const points = [
    { x: 0, y: 0, z: 0 }, { x: length, y: 0, z: 0 }, { x: length, y: width, z: 0 }, { x: 0, y: width, z: 0 },
    { x: 0, y: 0, z: height }, { x: length, y: 0, z: height }, { x: length, y: width, z: height }, { x: 0, y: width, z: height }
  ];
  return geometryFromPoints(points, label);
}

function fallbackGeometry(label) {
  return geometryFromPrism(4000, 300, 20, label);
}

function geometryFromPoints(points, label) {
  const min = { x: Infinity, y: Infinity, z: Infinity };
  const max = { x: -Infinity, y: -Infinity, z: -Infinity };

  for (const point of points) {
    min.x = Math.min(min.x, point.x);
    min.y = Math.min(min.y, point.y);
    min.z = Math.min(min.z, point.z);
    max.x = Math.max(max.x, point.x);
    max.y = Math.max(max.y, point.y);
    max.z = Math.max(max.z, point.z);
  }

  const bbox = { min, max, width: max.x - min.x, depth: max.y - min.y, height: max.z - min.z };
  const vertices = [
    { x: min.x, y: min.y, z: min.z }, { x: max.x, y: min.y, z: min.z }, { x: max.x, y: max.y, z: min.z }, { x: min.x, y: max.y, z: min.z },
    { x: min.x, y: min.y, z: max.z }, { x: max.x, y: min.y, z: max.z }, { x: max.x, y: max.y, z: max.z }, { x: min.x, y: max.y, z: max.z }
  ];
  const edgeIdx = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
  const edges = edgeIdx.map(([a,b], i) => ({ id: `e${i+1}`, from: vertices[a], to: vertices[b] }));
  const issues = bbox.height === 0 ? [{ id: 'flat-1', severity: 'high', code: 'ZERO_HEIGHT', message: 'Hoogte is 0.' }] : [];
  return { label, bbox, vertices, edges, issues };
}

function firstMatch(content, regex) {
  const match = content.match(regex);
  return match?.[1]?.trim();
}

function guessProfile(...values) {
  const joined = values.filter(Boolean).join(' ');
  return firstMatch(joined, /\b(H[EAEBM]\s?\d{2,4}|IPE\s?\d{2,4}|HEA\s?\d{2,4}|HEB\s?\d{2,4}|UNP\s?\d{2,4}|UPE\s?\d{2,4}|RHS\s?\d+x\d+x\d+|SHS\s?\d+x\d+x\d+)\b/i) || 'ONBEKEND';
}

function summarize(items) {
  const map = new Map();
  for (const item of items) map.set(item, (map.get(item) || 0) + 1);
  return [...map.entries()].sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count }));
}

function count(content, regex) { return (content.match(regex) || []).length; }
function num(v) { return Number(String(v).replace(/D/i, 'E')) || 0; }
function round2(v) { return Number(v.toFixed(2)); }
