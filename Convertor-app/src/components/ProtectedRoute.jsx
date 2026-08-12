import { Navigate } from 'react-router-dom';
import { getSession } from '../store/auth';

export default function ProtectedRoute({ children }) {
  const { token } = getSession();
  return token ? children : <Navigate to="/login" replace />;
}
