import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { dxfUrl, getJson } from '../api/client';
import ViewerCanvas from '../components/ViewerCanvas';

const PAN_STEP = 28;

export default function ViewerPage() {
  const { jobId } = useParams();
  const [viewer, setViewer] = useState(null);
  const [mode, setMode] = useState('top');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [showIssues, setShowIssues] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getJson(`/jobs/${jobId}/viewer`).then(setViewer).catch((e) => setError(e.message));
  }, [jobId]);

  const activeProjection = useMemo(() => {
    if (!viewer) return null;
    if (mode === '3d') return viewer.projections.top;
    return viewer.projections[mode] || viewer.projections.top;
  }, [viewer, mode]);

  function resetView() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  function movePan(deltaX, deltaY) {
    setPan((current) => ({ x: current.x + deltaX, y: current.y + deltaY }));
  }

  if (error) return <p className="error">{error}</p>;
  if (!viewer) return <p>Laden...</p>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Viewer</h2>
          <p className="muted">Bekijk projecties, issues en download direct de DXF.</p>
        </div>
        <div className="button-row">
          <Link className="button-link" to={`/jobs/${jobId}`}>Terug naar detail</Link>
          <a className="button-link" href={dxfUrl(jobId)}>DXF downloaden</a>
        </div>
      </div>

      <div className="toolbar card">
        <div className="button-row viewer-toolbar-row">
          {['top', 'front', 'side', '3d'].map((item) => (
            <button key={item} type="button" className={mode === item ? 'button-active' : ''} onClick={() => setMode(item)}>
              {item}
            </button>
          ))}
          <button type="button" onClick={() => setZoom((value) => Number((value + 0.1).toFixed(2)))}>Zoom +</button>
          <button type="button" onClick={() => setZoom((value) => Math.max(0.3, Number((value - 0.1).toFixed(2))))}>Zoom -</button>
          <button type="button" onClick={resetView}>Reset</button>
          <button type="button" onClick={() => setShowIssues((value) => !value)}>
            {showIssues ? 'Issues verbergen' : 'Issues tonen'}
          </button>
        </div>
        <div className="button-row viewer-toolbar-row viewer-pan-row">
          <button type="button" onClick={() => movePan(0, PAN_STEP)}>Pan omhoog</button>
          <button type="button" onClick={() => movePan(-PAN_STEP, 0)}>Pan links</button>
          <button type="button" onClick={() => movePan(PAN_STEP, 0)}>Pan rechts</button>
          <button type="button" onClick={() => movePan(0, -PAN_STEP)}>Pan omlaag</button>
        </div>
      </div>

      {activeProjection && (
        <div className="metrics-grid">
          <div className="card compact-card"><strong>Projectie</strong><div>{activeProjection.label || '-'}</div></div>
          <div className="card compact-card"><strong>Breedte</strong><div>{Math.round(activeProjection.width || 0)} mm</div></div>
          <div className="card compact-card"><strong>Hoogte</strong><div>{Math.round(activeProjection.height || 0)} mm</div></div>
          <div className="card compact-card"><strong>Issues</strong><div>{activeProjection.issueMarkers?.length || 0}</div></div>
        </div>
      )}

      <div className="page-grid viewer-grid">
        <div className="card viewer-card">
          <ViewerCanvas viewer={viewer} mode={mode} showIssues={showIssues} zoom={zoom} pan={pan} />
        </div>
        <div className="right-rail">
          <div className="card">
            <h3>Modelsamenvatting</h3>
            <pre className="pre-block">{JSON.stringify(viewer.summary, null, 2)}</pre>
          </div>
          <div className="card">
            <h3>Projecties</h3>
            <ul className="muted flow-list">
              {viewer.summary.projectionModes.map((projectionMode) => <li key={projectionMode}>{projectionMode}</li>)}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
