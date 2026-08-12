import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { postJson } from '../api/client';
import { saveSession } from '../store/auth';

export default function LoginPage() {
  const [form, setForm] = useState({ email: 'admin@demo.com', password: 'Admin123!', tenantKey: 'demo' });
  const [error, setError] = useState('');
  const navigate = useNavigate();
  async function submit(e) {
    e.preventDefault();
    try {
      const session = await postJson('/auth/login', form);
      saveSession(session);
      navigate('/dashboard');
    } catch (err) { setError(err.message); }
  }
  return (
    <div className="centered">
      <form className="card form" onSubmit={submit}>
        <h2>Inloggen</h2>
        <input placeholder="Tenant" value={form.tenantKey} onChange={(e) => setForm({ ...form, tenantKey: e.target.value })} />
        <input placeholder="E-mail" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <input type="password" placeholder="Wachtwoord" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && <p className="error">{error}</p>}
        <button>Inloggen</button>
        <div className="split-links"><Link to="/register">Account maken</Link><Link to="/reset">Reset</Link></div>
      </form>
    </div>
  );
}
