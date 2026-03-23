# Front - End

Bu klasor, LegalDoc Navigator projesinin modern web arayuzunu icerir.

## Hedef Teknoloji Yigini
- React
- Vite
- TailwindCSS

## Planlanan Klasor Yapisi

```text
Front - End/
├── public/
├── src/
│   ├── api/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   └── styles/
├── .env.example
├── .gitignore
└── README.md
```

## UI Hedefi
- Sol panel: PDF yukleme, surukle-birak ve yukleme ilerleme gostergesi
- Sag panel: Agent sohbet alani ve Markdown rapor gosterimi

## Backend Entegrasyonu
Frontend, asagidaki backend endpointlerini tuketecek sekilde gelistirilecektir:
- `POST /api/v1/document/upload`
- `POST /api/v1/agent/query`

## Ortam Degiskenleri
`.env.example` dosyasi:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Durum
Phase 6 kapsaminda React + Vite + Tailwind kurulumu ve UI implementasyonu tamamlandi.

## Calistirma

```bash
cd "Front - End"
npm install
npm run dev
```

Varsayilan gelistirme adresi: `http://localhost:5173`

Backend API varsayilan adresi: `http://localhost:8000`

## Gerceklesen Bilesenler
- React + Vite altyapisi (`index.jsx`, `App.jsx`)
- TailwindCSS konfigrasyonu
- Sol panel: PDF upload + progress bar + surukle-birak
- Sag panel: hukuki soru gonderme + markdown rapor gosterimi
- API servis katmani: `src/api/client.js` ve `src/api/legalApi.js`
- Hook katmani: `usePdfUpload`, `useAgentQuery`

## E2E Notu
- Frontend upload ve query akislarini backend endpointlerine bagli calistirir.
- Backend tarafinda gecerli `GEMINI_API_KEY` yoksa UI hata mesajini dogrudan gosterir.