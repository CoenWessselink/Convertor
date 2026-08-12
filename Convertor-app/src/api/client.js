const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:4000';

function headers(extra = {}) {
  const token = localStorage.getItem('convertor_token');
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra
  };
}

async function readJson(res) {
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    return { error: text || 'Onbekende response' };
  }
}

export async function postJson(path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers() },
    body: JSON.stringify(body)
  });
  const json = await readJson(res);
  if (!res.ok) throw new Error(json.error || 'Request mislukt');
  return json;
}

export async function getJson(path) {
  const res = await fetch(`${API_URL}${path}`, { headers: headers() });
  const json = await readJson(res);
  if (!res.ok) throw new Error(json.error || 'Request mislukt');
  return json;
}

export async function uploadFiles(files) {
  const data = new FormData();
  for (const file of files) data.append('files', file);
  const res = await fetch(`${API_URL}/jobs/upload`, { method: 'POST', headers: headers(), body: data });
  const json = await readJson(res);
  if (!res.ok) throw new Error(json.error || 'Upload mislukt');
  return json;
}

export async function createDemoSample(sampleKey = 'step') {
  return postJson('/jobs/demo-sample', { sampleKey });
}

export async function retryJob(jobId) {
  return postJson(`/jobs/${jobId}/retry`, {});
}

export function dxfUrl(jobId) {
  return `${API_URL}/jobs/${jobId}/dxf`;
}

export function apiBaseUrl() {
  return API_URL;
}
