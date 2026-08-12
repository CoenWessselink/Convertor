export function evaluateRules(parsed) {
  const issues = [];
  const warnings = [];
  const checks = [];
  const { source, model } = parsed;
  const dims = model.dimensions;

  pushCheck(checks, 'format-known', source.format !== 'UNKNOWN', 'Bestandsformaat is herkend.');
  pushCheck(checks, 'geometry-present', model.geometry?.vertices?.length >= 8, 'Basisgeometrie is beschikbaar.');

  if (dims.length <= 0) issues.push(rule('DIM_LENGTH_INVALID', 'error', 'Lengte is ongeldig of ontbreekt.'));
  if (dims.width <= 0) issues.push(rule('DIM_WIDTH_INVALID', 'error', 'Breedte is ongeldig of ontbreekt.'));
  if (dims.height <= 0) issues.push(rule('DIM_HEIGHT_INVALID', 'error', 'Hoogte is ongeldig of ontbreekt.'));
  if (model.profile === 'ONBEKEND') warnings.push(rule('PROFILE_UNKNOWN', 'warning', 'Profiel kon niet zeker worden afgeleid.'));

  if (source.format === 'DSTV') {
    const holes = model.operations.find((o) => o.type === 'holes')?.count || 0;
    pushCheck(checks, 'dstv-operations', true, `DSTV-operaties gevonden: ${holes} gaten.`);
  }

  if (source.format === 'STEP' && (model.entities.faces || 0) === 0) {
    warnings.push(rule('STEP_NO_FACES', 'warning', 'Geen ADVANCED_FACE entiteiten gevonden.'));
  }

  if (source.format === 'IFC' && (model.entities.total || 0) < 5) {
    warnings.push(rule('IFC_LOW_ENTITY_COUNT', 'warning', 'Weinig IFC-entiteiten gevonden; model kan incompleet zijn.'));
  }

  const confidence = calculateConfidence(parsed, issues, warnings, checks);
  return { issues, warnings, checks, confidence, summary: summarize(issues, warnings, checks) };
}

function calculateConfidence(parsed, issues, warnings, checks) {
  let score = 0.45;
  if (parsed.source.format !== 'UNKNOWN') score += 0.2;
  if (parsed.model.geometry?.vertices?.length >= 8) score += 0.15;
  if (parsed.model.profile && parsed.model.profile !== 'ONBEKEND') score += 0.1;
  score += Math.min(0.08, checks.filter((c) => c.passed).length * 0.02);
  score -= Math.min(0.3, issues.length * 0.12 + warnings.length * 0.04);
  return Number(Math.max(0.05, Math.min(0.98, score)).toFixed(2));
}

function summarize(issues, warnings, checks) {
  return {
    issueCount: issues.length,
    warningCount: warnings.length,
    passedChecks: checks.filter((c) => c.passed).length,
    failedChecks: checks.filter((c) => !c.passed).length
  };
}

function rule(code, severity, message) {
  return { code, severity, message };
}

function pushCheck(checks, code, passed, message) {
  checks.push({ code, passed, message });
}
