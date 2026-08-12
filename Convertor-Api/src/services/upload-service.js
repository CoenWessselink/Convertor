import fs from 'node:fs';
import path from 'node:path';
import multer from 'multer';
import { env } from '../config/env.js';

const uploadDir = path.join(env.uploadsDir);
fs.mkdirSync(uploadDir, { recursive: true });

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, uploadDir),
  filename: (req, file, cb) => {
    const safe = `${Date.now()}-${file.originalname.replace(/[^a-zA-Z0-9._-]/g, '_')}`;
    cb(null, safe);
  }
});

const allowedExt = new Set(['.step', '.stp', '.ifc', '.nc', '.nc1', '.dstv']);

export const upload = multer({
  storage,
  limits: {
    fileSize: env.uploadMaxBytes,
    files: env.uploadMaxFiles
  },
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname || '').toLowerCase();
    if (!allowedExt.has(ext)) {
      cb(new Error(`Bestandstype niet toegestaan: ${ext || 'onbekend'}`));
      return;
    }
    cb(null, true);
  }
});
