function projectEdge(edge, mode) {
  if (mode === 'front') return { id: edge.id, from: { x: edge.from.x, y: edge.from.z }, to: { x: edge.to.x, y: edge.to.z } };
  if (mode === 'side') return { id: edge.id, from: { x: edge.from.y, y: edge.from.z }, to: { x: edge.to.y, y: edge.to.z } };
  return { id: edge.id, from: { x: edge.from.x, y: edge.from.y }, to: { x: edge.to.x, y: edge.to.y } };
}

function projectPoint(point, mode) {
  if (!point) return { x: 0, y: 0 };
  if (mode === 'front') return { x: point.x, y: point.z };
  if (mode === 'side') return { x: point.y, y: point.z };
  return { x: point.x, y: point.y };
}

function boundsFromSegments(segments) {
  const values = segments.flatMap((segment) => [segment.from, segment.to]);
  const xs = values.map((point) => point.x);
  const ys = values.map((point) => point.y);
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
    width: Math.max(...xs) - Math.min(...xs),
    height: Math.max(...ys) - Math.min(...ys)
  };
}

function centerOfBounds(bounds) {
  return {
    x: bounds.minX + bounds.width / 2,
    y: bounds.minY + bounds.height / 2
  };
}

function projectionMeta(bbox, mode) {
  if (mode === 'front') {
    return {
      label: 'Vooraanzicht',
      width: bbox.width,
      height: bbox.height,
      axes: { horizontal: 'X', vertical: 'Z' }
    };
  }
  if (mode === 'side') {
    return {
      label: 'Zijaanzicht',
      width: bbox.depth,
      height: bbox.height,
      axes: { horizontal: 'Y', vertical: 'Z' }
    };
  }
  return {
    label: 'Bovenaanzicht',
    width: bbox.width,
    height: bbox.depth,
    axes: { horizontal: 'X', vertical: 'Y' }
  };
}

function buildProjection(mode, geometry, issues = []) {
  const segments = geometry.edges.map((edge) => projectEdge(edge, mode));
  const bounds = boundsFromSegments(segments);
  return {
    mode,
    ...projectionMeta(geometry.bbox, mode),
    bounds,
    center: centerOfBounds(bounds),
    segments,
    issueMarkers: issues.map((issue, index) => ({
      id: issue.id || `issue-${index + 1}`,
      severity: issue.severity || 'warning',
      code: issue.code || 'ISSUE',
      message: issue.message || 'Onbekende melding',
      position: projectPoint(issue.anchor || geometry.vertices?.[0], mode)
    }))
  };
}

function buildFaces(vertices) {
  if (!Array.isArray(vertices) || vertices.length < 8) return [];
  const faceIndices = [
    [0, 1, 2, 3],
    [4, 5, 6, 7],
    [0, 1, 5, 4],
    [2, 3, 7, 6],
    [1, 2, 6, 5],
    [0, 3, 7, 4]
  ];

  return faceIndices.map((indices, index) => ({
    id: `f${index + 1}`,
    vertices: indices.map((vertexIndex) => vertices[vertexIndex])
  }));
}

export function buildViewerPayload(result) {
  const geometry = result.model.geometry;
  const issues = [...(result.analysis.issues || []), ...(result.analysis.warnings || [])];
  const projections = {
    top: buildProjection('top', geometry, issues),
    front: buildProjection('front', geometry, issues),
    side: buildProjection('side', geometry, issues)
  };

  return {
    model: {
      label: geometry.label,
      bbox: geometry.bbox,
      vertices: geometry.vertices,
      edges: geometry.edges,
      faces: buildFaces(geometry.vertices)
    },
    projections,
    issueMarkers: {
      top: projections.top.issueMarkers,
      front: projections.front.issueMarkers,
      side: projections.side.issueMarkers
    },
    controls: {
      modes: ['top', 'front', 'side', '3d'],
      canPan: true,
      canZoom: true,
      canReset: true,
      canFit: true
    },
    summary: {
      issueCount: issues.length,
      bbox: geometry.bbox,
      projectionModes: Object.keys(projections)
    }
  };
}

function appendLayerDefinition(lines, layerName, colorNumber) {
  lines.push('0', 'LAYER', '2', layerName, '70', '0', '62', String(colorNumber), '6', 'CONTINUOUS');
}

function appendLineEntity(lines, layer, segment) {
  lines.push(
    '0', 'LINE',
    '8', layer,
    '10', String(segment.from.x),
    '20', String(segment.from.y),
    '30', '0',
    '11', String(segment.to.x),
    '21', String(segment.to.y),
    '31', '0'
  );
}

function appendCircleEntity(lines, layer, marker, radius) {
  lines.push(
    '0', 'CIRCLE',
    '8', layer,
    '10', String(marker.position.x),
    '20', String(marker.position.y),
    '30', '0',
    '40', String(radius)
  );
}

function appendTextEntity(lines, layer, x, y, text, height = 20) {
  lines.push(
    '0', 'TEXT',
    '8', layer,
    '10', String(x),
    '20', String(y),
    '30', '0',
    '40', String(height),
    '1', String(text)
  );
}

function appendProjectionEntities(lines, projection, layerPrefix) {
  for (const segment of projection.segments) {
    appendLineEntity(lines, `${layerPrefix}_GEOM`, segment);
  }

  const radius = Math.max(5, Math.min(projection.bounds.width || 10, projection.bounds.height || 10) * 0.02);
  for (const marker of projection.issueMarkers) {
    appendCircleEntity(lines, `${layerPrefix}_ISSUES`, marker, radius);
    appendTextEntity(lines, `${layerPrefix}_TEXT`, marker.position.x + radius * 1.4, marker.position.y + radius * 1.4, `${marker.code}: ${marker.message}`, radius * 1.6);
  }

  appendTextEntity(
    lines,
    `${layerPrefix}_TEXT`,
    projection.bounds.minX,
    projection.bounds.maxY + Math.max(25, projection.bounds.height * 0.08),
    `${projection.label} | ${projection.axes.horizontal}/${projection.axes.vertical} | ${Math.round(projection.width)} x ${Math.round(projection.height)} mm`,
    24
  );
}

export function generateDxf(viewerPayload) {
  const lines = [
    '0', 'SECTION', '2', 'HEADER',
    '9', '$INSUNITS', '70', '4',
    '0', 'ENDSEC',
    '0', 'SECTION', '2', 'TABLES',
    '0', 'TABLE', '2', 'LAYER', '70', '9'
  ];

  appendLayerDefinition(lines, 'TOP_GEOM', 7);
  appendLayerDefinition(lines, 'TOP_ISSUES', 1);
  appendLayerDefinition(lines, 'TOP_TEXT', 3);
  appendLayerDefinition(lines, 'FRONT_GEOM', 7);
  appendLayerDefinition(lines, 'FRONT_ISSUES', 1);
  appendLayerDefinition(lines, 'FRONT_TEXT', 3);
  appendLayerDefinition(lines, 'SIDE_GEOM', 7);
  appendLayerDefinition(lines, 'SIDE_ISSUES', 1);
  appendLayerDefinition(lines, 'SIDE_TEXT', 3);

  lines.push('0', 'ENDTAB', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES');

  appendProjectionEntities(lines, viewerPayload.projections.top, 'TOP');
  appendProjectionEntities(lines, viewerPayload.projections.front, 'FRONT');
  appendProjectionEntities(lines, viewerPayload.projections.side, 'SIDE');

  lines.push('0', 'ENDSEC', '0', 'EOF');
  return lines.join('\n');
}
