const lines = [
  'Fase D lokale bewijsfase',
  '',
  '1. Kopieer .env.example naar .env',
  '2. Start PostgreSQL of gebruik tijdelijk file mode voor tussenvalidatie',
  '3. Run npm install',
  '4. Run npm run migrate',
  '5. Run npm run seed',
  '6. Run npm test',
  '7. Run npm run dev',
  '',
  'Controleer daarna via de app:',
  '- login',
  '- upload STEP/IFC/NC1',
  '- jobs overzicht',
  '- jobdetail',
  '- viewer',
  '- dxf download',
  '- retry op failed jobs'
];
console.log(lines.join('\n'));
