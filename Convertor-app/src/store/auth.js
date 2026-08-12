export function getSession() {
  const token = localStorage.getItem('convertor_token');
  const user = localStorage.getItem('convertor_user');
  return { token, user: user ? JSON.parse(user) : null };
}

export function saveSession(session) {
  localStorage.setItem('convertor_token', session.token);
  localStorage.setItem('convertor_user', JSON.stringify(session.user));
}

export function clearSession() {
  localStorage.removeItem('convertor_token');
  localStorage.removeItem('convertor_user');
}
