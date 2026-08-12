export function validateBody(schema) {
  return (req, res, next) => {
    try {
      const payload = req.body || {};
      for (const [key, rules] of Object.entries(schema)) {
        const value = payload[key];
        if (rules.required && (value == null || value === '')) {
          throw new Error(`${key} is verplicht`);
        }
        if (value != null && rules.type === 'string' && typeof value !== 'string') {
          throw new Error(`${key} moet tekst zijn`);
        }
        if (typeof value === 'string' && rules.minLength && value.trim().length < rules.minLength) {
          throw new Error(`${key} moet minimaal ${rules.minLength} tekens bevatten`);
        }
      }
      next();
    } catch (error) {
      next(error);
    }
  };
}

export function requireFiles() {
  return (req, res, next) => {
    if (!req.files || req.files.length === 0) {
      next(new Error('Minimaal één bestand is verplicht'));
      return;
    }
    next();
  };
}
