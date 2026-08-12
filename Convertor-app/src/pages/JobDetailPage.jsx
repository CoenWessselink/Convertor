import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getJson, retryJob } from '../api/client';

export default function JobDetailPage() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setError('');
      setJob(await getJson(`/jobs/${jobId}`));
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, [jobId]);

  async function onRetry() {
    setBusy(true);
    try {
      await retryJob(jobId);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!job) return <p>Laden...</p>;

  const bbox = job.result?.viewer?.summary?.bbox || job.result?.model?.geometry?.bbox;
  const summary = job.result?.analysis?.summary;
  const checks = job.result?.analysis?.checks || [];
  const findings = job.result?.findings || [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Jobdetail</h2>
          <p className="muted">Bestand: {job.filename}</p>
        </div>
        <div className="button-row">
          <Link className="button-link" to="/jobs">Terug naar jobs</Link>
          {job.status === 'done' && <Link className="button-link" to={`/jobs/${jobId}/viewer`}>Open viewer</Link>}
          {job.status === 'failed' && <button onClick={onRetry} disabled={busy}>{busy ? 'Opnieuw verwerken...' : 'Opnieuw proberen'}</button>}
        </div>
      </div>

      <div className="card detail-grid">
        <div><strong>Status</strong><div><span className={`status status-${job.status}`}>{job.status}</span></div></div>
        <div><strong>Formaat</strong><div>{job.result?.source?.format || job.result?.format || '-'}</div></div>
        <div><strong>Confidence</strong><div>{job.result?.analysis?.confidence || job.result?.confidence || '-'}</div></div>
        <div><strong>Profiel</strong><div>{job.result?.model?.profile || '-'}</div></div>
      </div>

      {bbox && (
        <div className="metrics-grid">
          <div className="card compact-card"><strong>Lengte</strong><div>{Math.round(bbox.width)} mm</div></div>
          <div className="card compact-card"><strong>Breedte</strong><div>{Math.round(bbox.depth)} mm</div></div>
          <div className="card compact-card"><strong>Hoogte</strong><div>{Math.round(bbox.height)} mm</div></div>
          <div className="card compact-card"><strong>Issues</strong><div>{summary?.issueCount ?? 0}</div></div>
        </div>
      )}

      <div className="page-grid">
        <div>
          <div className="card">
            <h3>Findings</h3>
            {findings.length === 0 ? <p className="muted">Geen findings beschikbaar.</p> : <ul>{findings.map((finding) => <li key={finding}>{finding}</li>)}</ul>}
          </div>

          <div className="card">
            <h3>Checks</h3>
            {checks.length === 0 ? (
              <p className="muted">Geen checks beschikbaar.</p>
            ) : (
              <div className="stack-list">
                {checks.map((check) => (
                  <div key={check.code} className="check-row">
                    <span className={`status ${check.passed ? 'status-done' : 'status-failed'}`}>{check.passed ? 'OK' : 'FOUT'}</span>
                    <div>
                      <strong>{check.code}</strong>
                      <div className="muted">{check.message}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="right-rail">
          <div className="card">
            <h3>Metrics</h3>
            <pre className="pre-block">{JSON.stringify(job.result?.metrics || {}, null, 2)}</pre>
          </div>
          <div className="card">
            <h3>Analyse</h3>
            <pre className="pre-block">{JSON.stringify(job.result?.analysis?.summary || {}, null, 2)}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}
