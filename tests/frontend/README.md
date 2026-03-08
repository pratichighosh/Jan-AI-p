# CAIS Frontend

React PWA for the Citizen Application Intelligence System.

## Tech Stack
- React 18 + Vite, Axios, React Dropzone, Framer Motion, Lucide React, Recharts

## Setup
```bash
cd frontend
cp .env.example .env
npm install
npm run dev     # http://localhost:5173
npm run build   # production build in ./dist
```

## Screens
Splash → Language Select (22 Indian languages) → Home Dashboard → Upload → Results

## Environment Variables
| Variable | Default | Description |
|---|---|---|
| VITE_API_URL | http://localhost:8000/api/v1 | Backend base URL |
