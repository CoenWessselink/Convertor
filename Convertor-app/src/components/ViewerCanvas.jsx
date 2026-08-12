const VIEWBOX_WIDTH = 960;
const VIEWBOX_HEIGHT = 560;

function readProjection(viewer, mode) {
  if (mode === '3d') {
    return {
      ...viewer.projections.top,
      segments: viewer.model.edges.map((edge) => ({
        id: edge.id,
        from: { x: edge.from.x - edge.from.y * 0.35, y: edge.from.z + edge.from.y * 0.35 },
        to: { x: edge.to.x - edge.to.y * 0.35, y: edge.to.z + edge.to.y * 0.35 }
      })),
      issueMarkers: viewer.issueMarkers?.top || []
    };
  }
  return viewer.projections[mode] || viewer.projections.top;
}

function boundsFromProjection(projection) {
  const points = projection.segments.flatMap((segment) => [segment.from, segment.to]);
  const allPoints = points.length ? points : [{ x: 0, y: 0 }, { x: 100, y: 100 }];
  const xs = allPoints.map((point) => point.x);
  const ys = allPoints.map((point) => point.y);
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys)
  };
}

export default function ViewerCanvas({ viewer, mode = 'top', showIssues = true, zoom = 1, pan = { x: 0, y: 0 } }) {
  const projection = readProjection(viewer, mode);
  const bounds = boundsFromProjection(projection);
  const spanX = Math.max(1, bounds.maxX - bounds.minX);
  const spanY = Math.max(1, bounds.maxY - bounds.minY);
  const padding = 70;
  const scale = Math.min((VIEWBOX_WIDTH - padding * 2) / spanX, (VIEWBOX_HEIGHT - padding * 2) / spanY) * zoom;

  const mapPoint = (point) => ({
    x: (point.x - bounds.minX) * scale + padding + pan.x,
    y: VIEWBOX_HEIGHT - ((point.y - bounds.minY) * scale + padding) + pan.y
  });

  const issueMarkers = projection.issueMarkers || viewer.issueMarkers?.[mode] || [];

  return (
    <svg viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`} className="viewer">
      <rect x="0" y="0" width={VIEWBOX_WIDTH} height={VIEWBOX_HEIGHT} fill="#ffffff" />
      <rect x="18" y="18" width={VIEWBOX_WIDTH - 36} height={VIEWBOX_HEIGHT - 36} rx="18" fill="#f8fafc" stroke="#cbd5e1" />

      {projection.segments.map((segment) => {
        const from = mapPoint(segment.from);
        const to = mapPoint(segment.to);
        return <line key={segment.id} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#0f172a" strokeWidth="2.5" />;
      })}

      {showIssues && issueMarkers.map((marker) => {
        const point = mapPoint(marker.position);
        return (
          <g key={marker.id}>
            <circle cx={point.x} cy={point.y} r="8" fill={marker.severity === 'error' ? '#dc2626' : '#f59e0b'} />
            <circle cx={point.x} cy={point.y} r="14" fill="none" stroke={marker.severity === 'error' ? '#dc2626' : '#f59e0b'} strokeWidth="2" opacity="0.45" />
            <text x={point.x + 16} y={point.y - 10} fontSize="13" fill="#0f172a">{marker.code}</text>
            <text x={point.x + 16} y={point.y + 8} fontSize="11" fill="#475569">{marker.message}</text>
          </g>
        );
      })}

      <text x="32" y="42" fontSize="16" fill="#0f172a">{projection.label || 'Viewer'}</text>
      <text x="32" y="62" fontSize="12" fill="#64748b">
        {projection.axes ? `Assen: ${projection.axes.horizontal}/${projection.axes.vertical}` : 'Projectie'}
      </text>
    </svg>
  );
}
