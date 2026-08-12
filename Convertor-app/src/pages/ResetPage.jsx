import { useState } from 'react';
import { postJson } from '../api/client';

export default function ResetPage() {
  const [step, setStep] = useState(1);
  const [request, setRequest] = useState({ email: 'admin@demo.com', tenantKey: 'demo' });
  const [resetToken, setResetToken] = useState('');
  const [password, setPassword] = useState('Admin123!');
  const [message, setMessage] = useState('');
  async function sendRequest(e) {
    e.preventDefault();
    const res = await postJson('/auth/request-reset', request);
    setResetToken(res.token || '');
    setMessage(res.token ? `Reset token: ${res.token}` : 'Reset aangevraagd');
    setStep(2);
  }
  async function complete(e) {
    e.preventDefault();
    await postJson('/auth/reset-password', { token: resetToken, password });
    setMessage('Wachtwoord aangepast');
  }
  return (
    <div className="centered">
      <div className="card form">
        <h2>Wachtwoord reset</h2>
        {step === 1 ? <form onSubmit={sendRequest}><input value={request.tenantKey} onChange={(e)=>setRequest({...request, tenantKey:e.target.value})} /><input value={request.email} onChange={(e)=>setRequest({...request, email:e.target.value})} /><button>Reset aanvragen</button></form> : <form onSubmit={complete}><input value={resetToken} onChange={(e)=>setResetToken(e.target.value)} /><input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} /><button>Opslaan</button></form>}
        {message && <p>{message}</p>}
      </div>
    </div>
  );
}
