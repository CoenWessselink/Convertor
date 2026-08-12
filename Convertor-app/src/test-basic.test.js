import test from 'node:test';
import assert from 'node:assert/strict';

test('basis', () => {
  assert.equal(1 + 1, 2);
});

test('viewer controls config object shape', () => {
  const controls = { canPan: true, canZoom: true, canFit: true, canReset: true };
  assert.equal(controls.canPan, true);
  assert.equal(controls.canFit, true);
});
