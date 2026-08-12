import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { clearSession, getSession } from '../store/auth';

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/jobs', label: 'Jobs' },
  { to: '/upload', label: 'Upload' }
];

export default function Layout() {
  const navigate = useNavigate();
  const session = getSession();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div>
          <h1>Convertor</h1>
          <p className="sidebar-subtitle">STEP, IFC en NC1 naar viewer + DXF</p>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="card sidebar-card">
          <strong>Snelle route</strong>
          <p className="muted">Upload een bestand of maak eerst een demo-job om direct viewer en DXF te zien.</p>
        </div>

        <div className="userbox">
          <div>{session.user?.name}</div>
          <div className="muted">{session.user?.tenantKey}</div>
          <button onClick={() => { clearSession(); navigate('/login'); }}>Uitloggen</button>
        </div>
      </aside>
      <main className="main"><Outlet /></main>
    </div>
  );
}
