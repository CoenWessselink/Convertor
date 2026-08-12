import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getJson } from '../api/client';

export default function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');

  useEffect(() => {
    let active = true;
    const fetchJobs = async () => {
      try {
        const data = await getJson('/jobs');
        if (active) {
          setJobs(data.jobs || []);
          setError('');
          setLoading(false);
        }
      } catch (err) {
        if (active) {
          setError(err.message);
          setLoading(false);
        }
      }
    };
    fetchJobs();
    const id = setInterval(fetchJobs, 3000);
    return () => { active = false; clearInterval(id); };
  }, []);

  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      const matchesFilter = filter === 'all' ? true : job.status === filter;
      const text = `${job.filename || ''} ${job.format || ''} ${job.profile || ''}`.toLowerCase();
      const matchesQuery = text.includes(query.toLowerCase());
      return matchesFilter && matchesQuery;
    });
  }, [jobs, filter, query]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Jobs</h2>
          <p className="muted">Overzicht van uploads, analyses, viewer en DXF-downloads.</p>
        </div>
        <div className="button-row">
          <Link className="button-link" to="/upload">Nieuw uploaden</Link>
        </div>
      </div>

      <div className="card toolbar-grid">
        <input placeholder="Zoek op bestand, formaat of profiel" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select value={filter} onChange={(event) => setFilter(event.target.value)}>
          <option value="all">Alle statussen</option>
          <option value="done">Gereed</option>
          <option value="processing">Processing</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {loading && <p>Laden...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && filteredJobs.length === 0 && <p className="muted">Nog geen jobs gevonden voor deze selectie.</p>}

      <div className="table-wrap card">
        <table>
          <thead>
            <tr>
              <th>Bestand</th>
              <th>Status</th>
              <th>Formaat</th>
              <th>Profiel</th>
              <th>Confidence</th>
              <th>Issues</th>
              <th>Acties</th>
            </tr>
          </thead>
          <tbody>
            {filteredJobs.map((job) => (
              <tr key={job.id}>
                <td>{job.filename}</td>
                <td><span className={`status status-${job.status}`}>{job.status}</span></td>
                <td>{job.format || '-'}</td>
                <td>{job.profile || '-'}</td>
                <td>{job.confidence ?? '-'}</td>
                <td>{job.issueCount ?? 0}</td>
                <td>
                  <div className="inline-actions">
                    <Link to={`/jobs/${job.id}`}>Detail</Link>
                    {job.status === 'done' && <Link to={`/jobs/${job.id}/viewer`}>Viewer</Link>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
