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
- `LMSTUDIO_BASE_URL`
- `LMSTUDIO_API_KEY`
- `LMSTUDIO_MODEL`
- `HF_EMBEDDING_MODEL`
- `HF_EMBEDDING_BATCH_SIZE`
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
3. Chunk'lar lokal HuggingFace embedding modeli ile vektorlestirilir.
4. ChromaDB'ye persistent olarak yazilir.
5. Sorgu geldigi zaman LangGraph ajan akisi LM Studio (OpenAI uyumlu local server) uzerinden calisir:
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
- LM Studio'da Local Server acik olmali ve varsayilan olarak `http://localhost:1234/v1` adresinde erisilebilir olmalidir.
- Embedding modeli degistiginde eski vektorlerin uyumsuz olmasini engellemek icin `./data/chroma` klasorunu temizleyin:
	```bash
	cd "Back - End"
	/usr/bin/python3 scripts/clear_chroma.py
	```