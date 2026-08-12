export function errorHandler(err, req, res, next) {
  console.error(err);
  const status = err.statusCode || 400;
  res.status(status).json({ error: err.message || 'Onbekende fout' });
}
