# Convertor-Api

Fase C build voor lokale validatie en platform-hardening.

## Ondersteunde modi
- Bestandopslag fallback zonder `DATABASE_URL`
- PostgreSQL zodra `DATABASE_URL` is ingevuld

## Starten
```bash
copy .env.example .env
npm install
npm run migrate
npm run seed
npm run dev
```

## Testen
```bash
npm test
```

## Belangrijk
Deze fase voegt een repository-laag, inputvalidatie, rate limiting en retry-flow toe.
Voor 100% afronding blijft fase D met lokale volledige bewijsvoering nodig.
