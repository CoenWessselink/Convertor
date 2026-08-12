import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { postJson } from '../api/client';
import { saveSession } from '../store/auth';

export default function RegisterPage() {
  const [form, setForm] = useState({ name: 'Demo Admin', email: 'admin@demo.com', password: 'Admin123!', tenantKey: 'demo' });
  const [error, setError] = useState('');
  const navigate = useNavigate();
  async function submit(e) {
    e.preventDefault();
    try {
      const session = await postJson('/auth/register', form);
      saveSession(session);
      navigate('/dashboard');
    } catch (err) { setError(err.message); }
  }
  return (
    <div className="centered">
      <form className="card form" onSubmit={submit}>
        <h2>Registreren</h2>
        <input placeholder="Naam" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input placeholder="Tenant" value={form.tenantKey} onChange={(e) => setForm({ ...form, tenantKey: e.target.value })} />
        <input placeholder="E-mail" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <input type="password" placeholder="Wachtwoord" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && <p className="error">{error}</p>}
        <button>Account maken</button>
        <Link to="/login">Terug naar login</Link>
      </form>
    </div>
  );
}
