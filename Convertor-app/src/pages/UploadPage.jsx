import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { createDemoSample, uploadFiles } from '../api/client';

const allowed = ['.step', '.stp', '.ifc', '.nc', '.nc1', '.dstv'];

export default function UploadPage() {
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [selectedNames, setSelectedNames] = useState([]);
  const [sampleKey, setSampleKey] = useState('step');
  const navigate = useNavigate();

  const helperText = useMemo(() => `Toegestaan: ${allowed.join(', ')}`, []);

  async function handleFiles(fileList) {
    const files = [...fileList];
    setSelectedNames(files.map((file) => file.name));
    const invalid = files.filter((file) => !allowed.some((ext) => file.name.toLowerCase().endsWith(ext)));
    if (invalid.length) {
      setMessage(`Niet toegestaan: ${invalid.map((file) => file.name).join(', ')}`);
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      const result = await uploadFiles(files);
      setMessage(`${result.jobs.length} job(s) verwerkt.`);
      navigate('/jobs');
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDemo() {
    try {
      setBusy(true);
      setMessage('');
      const job = await createDemoSample(sampleKey);
      navigate(`/jobs/${job.id}/viewer`);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-grid">
      <div>
        <div className="page-header">
          <div>
            <h2>Upload</h2>
            <p className="muted">Laad STEP, IFC of NC1/DSTV direct in. Na verwerking kun je meteen viewer en DXF openen.</p>
          </div>
          <div className="button-row">
            <Link className="button-link" to="/jobs">Jobs bekijken</Link>
          </div>
        </div>

        <label className="dropzone">
          <input type="file" multiple onChange={(event) => handleFiles(event.target.files)} hidden />
          <div className="dropzone-inner">
            <strong>{busy ? 'Bezig met analyseren...' : 'Klik om bestanden te kiezen'}</strong>
            <span className="muted">{helperText}</span>
          </div>
        </label>

        {selectedNames.length > 0 && (
          <div className="card">
            <strong>Geselecteerd</strong>
            <ul>
              {selectedNames.map((name) => <li key={name}>{name}</li>)}
            </ul>
          </div>
        )}

        {message && <p className={message.startsWith('Niet toegestaan') ? 'error' : ''}>{message}</p>}
      </div>

      <div className="right-rail">
        <div className="card">
          <h3>Demo zonder eigen bestand</h3>
          <p className="muted">Maak direct een voorbeeldjob aan inclusief viewer en DXF-download.</p>
          <select value={sampleKey} onChange={(event) => setSampleKey(event.target.value)}>
            <option value="step">Demo STEP</option>
            <option value="ifc">Demo IFC</option>
            <option value="nc1">Demo NC1</option>
          </select>
          <div className="button-row top-gap">
            <button type="button" onClick={handleDemo} disabled={busy}>{busy ? 'Bezig...' : 'Demo-job maken'}</button>
          </div>
        </div>

        <div className="card">
          <h3>Flow</h3>
          <ol className="muted flow-list">
            <li>Bestand kiezen of demo aanmaken</li>
            <li>Analyse en rules-engine draaien</li>
            <li>Jobdetail openen</li>
            <li>Viewer openen</li>
            <li>DXF downloaden</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
