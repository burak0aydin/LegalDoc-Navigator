# Back - End

Bu klasor, LegalDoc Navigator projesinin FastAPI tabanli backend katmanini icerir.

## Klasor Yapisi

```text
Back - End/
├── api/
│   ├── __init__.py
│   └── routes.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   └── logger.py
├── data/
│   └── .gitkeep
├── database/
│   ├── __init__.py
│   └── vector_store.py
├── services/
│   ├── __init__.py
│   ├── pdf_processor.py
│   ├── embedding.py
│   └── retrieval.py
├── agent/
│   ├── __init__.py
│   ├── graph.py
│   └── nodes.py
├── .env.example
├── .gitignore
├── requirements.txt
├── main.py
└── README.md
```

## Python Sanal Ortam (venv) Kurulumu

Asagidaki adimlar backend gelistirme ortamini hazirlar:

```bash
cd "Back - End"

# 1) Sanal ortam olustur
python3 -m venv venv

# 2) Sanal ortami aktive et
# macOS / Linux:
source venv/bin/activate
# Windows (PowerShell):
# .\venv\Scripts\Activate.ps1

# 3) Bagimliliklari yukle
pip install --upgrade pip
pip install -r requirements.txt

# 4) Ortam degiskenlerini hazirla
cp .env.example .env

# 5) Uygulamayi calistir (ilerleyen fazlarda endpointler aktif olacak)
uvicorn main:app --reload
```

## Ortam Degiskenleri

`.env.example` dosyasinda asagidaki temel degiskenler bulunur:
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `GEMINI_EMBEDDING_MODEL`
- `VECTOR_DB_PROVIDER`
- `CHROMA_PERSIST_DIR`
- `CHROMA_COLLECTION_NAME`
- `APP_ENV`
- `LOG_LEVEL`
- `API_V1_PREFIX`

## Calisan API Uclari
- `GET /health`
- `POST /api/v1/document/upload`
- `POST /api/v1/agent/query`

## Akis
1. PDF upload edilir.
2. PDF metni cikartilir ve hukuki baglami koruyacak sekilde chunk'lanir.
3. Chunk'lar Gemini embedding ile vektorlestirilir.
4. ChromaDB'ye persistent olarak yazilir.
5. Sorgu geldigi zaman LangGraph ajan akisi calisir:
	 - Analyze Query
	 - Retrieve
	 - Grade Documents
	 - Generate

## Gozlemlenebilirlik
- `main.py` icinde request timing middleware bulunur (`duration_ms` loglanir).
- `agent/nodes.py` node gecislerini loglar.
- `agent/graph.py` conditional routing kararlarini loglar.

## E2E Test Komutlari

Ornek PDF olusturma:
```bash
cd "Back - End"
/usr/bin/python3 - <<'PY'
import fitz
from pathlib import Path

out = Path('data/sample_kvkk.pdf')
out.parent.mkdir(parents=True, exist_ok=True)
doc = fitz.open()
page = doc.new_page()
page.insert_text((72, 72), 'MADDE 1 - Kisisel veriler hukuka uygun islenir.')
doc.save(out)
doc.close()
print(out)
PY
```

Upload testi:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/document/upload" -F "file=@data/sample_kvkk.pdf"
```

Query testi:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/agent/query" \
	-H "Content-Type: application/json" \
	-d '{"query":"KVKK kapsaminda acik riza nedir?","max_attempts":2}'
```

## Bilinen Gereksinim
- Basarili embedding/agent yaniti icin gecerli `GEMINI_API_KEY` zorunludur.
- Bu anahtar tanimli degilse endpointler kontrollu sekilde `500` ve acik hata mesaji dondurur.