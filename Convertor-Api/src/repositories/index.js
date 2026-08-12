import { env } from '../config/env.js';
import { fileRepository } from './file-repository.js';
import { postgresRepository } from './postgres-repository.js';

export const repository = env.dbMode === 'postgres' ? postgresRepository : fileRepository;
