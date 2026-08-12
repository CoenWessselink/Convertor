import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { createDemoSample, getJson } from '../api/client';
import { getSession } from '../store/auth';

const sampleOptions = [
  { key: 'step', label: 'Demo STEP' },
  { key: 'ifc', label: 'Demo IFC' },
  { key: 'nc1', label: 'Demo NC1' }
];

export default function DashboardPage() {
  const { user } = getSession();
  const [jobs, setJobs] = useState([]);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  async function loadJobs() {
    try {
      const data = await getJson('/jobs');
      setJobs(data.jobs || []);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadJobs();
  }, []);

  async function handleCreateDemo(sampleKey) {
    try {
      setBusy(sampleKey);
      setError('');
      await createDemoSample(sampleKey);
      await loadJobs();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  const latestJob = jobs[0];
  const stats = useMemo(() => {
    const done = jobs.filter((job) => job.status === 'done').length;
    const failed = jobs.filter((job) => job.status === 'failed').length;
    const processing = jobs.filter((job) => job.status === 'processing' || job.status === 'pending').length;
    return { total: jobs.length, done, failed, processing };
  }, [jobs]);

  return (
    <div className="page-grid">
      <div>
        <div className="page-header">
          <div>
            <h2>Dashboard</h2>
            <p className="muted">Ingelogd als {user?.email}. Bouw direct een demo-job of upload je eigen bestand.</p>
          </div>
          <div className="button-row">
            <Link className="button-link" to="/upload">Nieuw uploaden</Link>
            <Link className="button-link" to="/jobs">Jobs openen</Link>
          </div>
        </div>

        <div className="metrics-grid">
          <div className="card compact-card"><strong>Totaal jobs</strong><div className="big-number">{stats.total}</div></div>
          <div className="card compact-card"><strong>Gereed</strong><div className="big-number">{stats.done}</div></div>
          <div className="card compact-card"><strong>In verwerking</strong><div className="big-number">{stats.processing}</div></div>
          <div className="card compact-card"><strong>Fouten</strong><div className="big-number">{stats.failed}</div></div>
        </div>

        <div className="card">
          <h3>Demo starten</h3>
          <p className="muted">Hiermee maak je zonder eigen bestand direct een converter-job met viewer en DXF-download.</p>
          <div className="button-row">
            {sampleOptions.map((option) => (
              <button key={option.key} type="button" onClick={() => handleCreateDemo(option.key)} disabled={Boolean(busy)}>
                {busy === option.key ? 'Bezig...' : option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          <h3>Recente jobs</h3>
          {jobs.length === 0 ? (
            <p className="muted">Nog geen jobs. Start met een demo-job of upload een STEP, IFC of NC1-bestand.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Bestand</th><th>Status</th><th>Formaat</th><th>Confidence</th><th>Issues</th><th>Actie</th></tr>
                </thead>
                <tbody>
                  {jobs.slice(0, 6).map((job) => (
                    <tr key={job.id}>
                      <td>{job.filename}</td>
                      <td><span className={`status status-${job.status}`}>{job.status}</span></td>
                      <td>{job.format || '-'}</td>
                      <td>{job.confidence ?? '-'}</td>
                      <td>{job.issueCount ?? 0}</td>
                      <td><Link to={`/jobs/${job.id}`}>Openen</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="right-rail">
        <div className="card">
          <h3>Gebruiker</h3>
          <div className="stack-list">
            <div><strong>Naam</strong><div>{user?.name}</div></div>
            <div><strong>Tenant</strong><div>{user?.tenantKey}</div></div>
            <div><strong>Rol</strong><div>{user?.role}</div></div>
          </div>
        </div>

        <div className="card">
          <h3>Laatste viewer</h3>
          {!latestJob ? (
            <p className="muted">Nog geen viewer beschikbaar.</p>
          ) : (
            <div className="stack-list">
              <div><strong>Bestand</strong><div>{latestJob.filename}</div></div>
              <div><strong>Status</strong><div>{latestJob.status}</div></div>
              <div className="button-row">
                <Link className="button-link" to={`/jobs/${latestJob.id}`}>Jobdetail</Link>
                {latestJob.status === 'done' && <Link className="button-link" to={`/jobs/${latestJob.id}/viewer`}>Viewer openen</Link>}
              </div>
            </div>
          )}
        </div>

        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
