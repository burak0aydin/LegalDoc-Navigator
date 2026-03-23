# LegalDoc Navigator

LegalDoc Navigator, hukuki metinleri (mevzuat, mahkeme kararları, sozlesmeler) analiz eden, RAG ve LangGraph tabanli agentik bir karar destek sistemidir. Sistem, yuklenen PDF dokumanlardan baglama uygun parcaciklar cikarir, vektor veritabaninda semantik arama yapar ve kullanici sorusuna gore ozet rapor uretir.

## Vizyon
- Uzun hukuki metinlerde ilgili maddelere hizli erisim
- Soru odakli, kaynak baglamini koruyan ozetleme
- Moduler, olceklenebilir ve uretime hazir bir full-stack mimari

## Mimari Ozet
- Back - End: FastAPI, LangChain, LangGraph, PyMuPDF, ChromaDB, Gemini API
- Front - End: React + Vite + TailwindCSS

Ana klasor yapisi:

```text
LegalDoc-Navigator/
├── Back - End/
├── Front - End/
├── plan.md
└── README.md
```

Detayli teknik kurulumlar icin:
- `Back - End/README.md`
- `Front - End/README.md`

## Gelistirici Ekip
- Burak Aydin - 1911012833
- Sedef Gizem Orulluoglu - 2211012047
- Mert Acar - 2311012072

## Hizli Baslangic

### 1) Backend
```bash
cd "Back - End"
/usr/bin/python3 -m pip install -r requirements.txt
cp .env.example .env
/usr/bin/python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 2) Frontend
```bash
cd "Front - End"
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### 3) Erisim
- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/health`
- Swagger: `http://127.0.0.1:8000/docs`

## API Uc Noktalari
- `POST /api/v1/document/upload`
- `POST /api/v1/agent/query`

## Phase 7 Test Ozeti
- Backend ve frontend eszamanli calistirildi.
- Ornek hukuki PDF (`Back - End/data/sample_kvkk.pdf`) ile upload ve query endpointleri test edildi.
- Gemini API anahtari olmadigi durumda sistemin hata yonetimi dogrulandi:
	- Upload: `500` ve acik hata mesaji (embedding olusturulamadi)
	- Query: `500` ve acik hata mesaji (agent akisi basarisiz)
- Request sure loglari aktif: `main.py` middleware ile `duration_ms` kayit altina aliniyor.
- Node bazli graph loglari aktif: `analyze_query`, `retrieve_documents`, `grade_documents`, `generate_answer`.

## Not
Tam uctan uca basarili yanit uretimi icin `.env` dosyasinda gecerli `GEMINI_API_KEY` girilmelidir.


