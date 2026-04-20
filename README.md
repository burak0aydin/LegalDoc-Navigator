# LegalDoc Navigator

LegalDoc Navigator; mevzuat, mahkeme kararı ve sözleşme gibi hukuki PDF metinlerini yükleyip anlamlı parçalara bölen, vektör veritabanına indeksleyen ve kullanıcı sorusuna kaynak odaklı yanıt üreten bir karar destek sistemidir.

Bu README, projeyi baştan sona anlaman için hazırlanmış kapsamlı dokümantasyondur:
- Sistem nasıl çalışır?
- Mimari katmanlar nelerdir?
- Hangi dosya ne iş yapar?
- Kurulum ve çalıştırma adımları nelerdir?

## Geliştirici Ekip
- Burak Aydın - 1911012833
- Sedef Gizem Orulluoğlu - 2211012047
- Mert Acar - 2311012072

## Kullanılan Teknolojiler
- Backend -> FastAPI, LangChain, LangGraph, PyMuPDF, ChromaDB, sentence-transformers, LM Studio (OpenAI uyumlu local server)
- Frontend -> React, Vite, TailwindCSS, Axios, React Markdown
- Veri -> Chroma persistent storage (`Back - End/data/chroma`), yüklenen dosyalar (`Back - End/data/uploads`)

## Sistem Nasıl Çalışır? (Uçtan Uca Akış)
1. Kullanıcı arayüzden bir PDF yükler.
2. Backend PDF dosyasını güvenli biçimde diske kaydeder.
3. PDF metni çıkarılır ve hukuki bağlamı koruyacak şekilde chunk'lara ayrılır.
4. Her chunk embedding modeline gönderilir ve vektöre dönüştürülür.
5. Vektörler ChromaDB koleksiyonuna yazılır.
6. Kullanıcı hukuki soru sorar.
7. Soru embedding'e çevrilir, semantik arama + keyword arama yapılır.
8. Sonuçlar opsiyonel reranker ile yeniden sıralanır.
9. LangGraph akışı sırayla çalışır:
	 - Analyze Query
	 - Retrieve Documents
	 - Grade Documents
	 - Generate Answer
10. LLM, ilgili kaynakları kullanarak markdown cevap üretir ve frontend'e döner.

## Proje Mimarisi

```text
LegalDoc-Navigator/
├── Back - End/
├── Front - End/
├── plan.md
└── README.md
```

### Backend Mimari Katmanları
- API Katmanı -> HTTP endpoint'ler, request/response doğrulama
- Servis Katmanı -> PDF işleme, embedding, retrieval
- Agent Katmanı -> LangGraph node'ları ve yönlendirme
- Veri Katmanı -> Chroma vektör veritabanı erişimi
- Core Katmanı -> Konfigürasyon ve loglama

### Frontend Mimari Katmanları
- UI Katmanı -> Sayfalar ve bileşenler
- Hook Katmanı -> Durum yönetimi ve asenkron işlemler
- API Katmanı -> Backend ile HTTP iletişimi
- Stil Katmanı -> Tailwind tema + global CSS

## Dosya ve Dizin Açıklamaları (Detaylı)

## Klasor Yapisi

### Back - End

```text
Back - End/                         -> Backend ana klasoru; FastAPI, RAG ve agent akisini barindirir.
├── api/                            -> HTTP isteklerini karsilayan API katmani.
│   ├── __init__.py                 -> api klasorunu Python paketi olarak tanimlar.
│   └── routes.py                   -> /document/upload ve /agent/query endpointlerini, request/response semalarini ve hata yonetimini icerir.
├── core/                           -> Uygulama genelinde ortak kullanilan ayar ve altyapi katmani.
│   ├── __init__.py                 -> core klasorunu paket olarak tanimlar.
│   ├── config.py                   -> .env degiskenlerini okuyup Settings nesnesi haline getirir, upload dizinini olusturur.
│   └── logger.py                   -> Log seviyesini ve log formatini merkezi olarak ayarlar.
├── data/                           -> Uygulamanin urettigi lokal verilerin saklandigi alan.
│   └── .gitkeep                    -> Bos klasorun git tarafinda korunmasini saglar.
├── database/                       -> Vektor veritabani ile iletisim katmani.
│   ├── __init__.py                 -> database klasorunu paket olarak tanimlar.
│   └── vector_store.py             -> ChromaDB baglantisi, upsert, similarity search, keyword search ve koleksiyon yonetimi islemleri.
├── services/                       -> Is kurallarini tasiyan servis katmani.
│   ├── __init__.py                 -> services klasorunu paket olarak tanimlar.
│   ├── pdf_processor.py            -> PDF kaydetme, metin cikarma ve hukuki baglami koruyan chunklama adimlari.
│   ├── embedding.py                -> HuggingFace tabanli embedding modeli ile metin/sorgu vektoru uretimi.
│   └── retrieval.py                -> Semantik arama + keyword arama + reranking ile ilgili parcalari secme.
├── agent/                          -> LangGraph tabanli karar verici agent katmani.
│   ├── __init__.py                 -> agent klasorunu paket olarak tanimlar.
│   ├── graph.py                    -> Node'larin baglanti sirasini ve kosullu gecisleri (retry/generate) tanimlar.
│   └── nodes.py                    -> Analyze, Retrieve, Grade, Generate node fonksiyonlarini ve state yonetimini icerir.
├── scripts/                        -> Yardimci bakim ve operasyon scriptleri.
│   └── clear_chroma.py             -> Chroma kalici verisini temizleyerek yeni embedding modeliyle temiz baslangic saglar.
├── clear_chroma.py                 -> Kisa yoldan ayni temizleme islemini yapan alternatif script.
├── .env.example                    -> Ortam degiskenleri sablonu (LM Studio, embedding, Chroma, CORS vb.).
├── .gitignore                      -> venv, gecici dosyalar ve yerel dosyalarin gite gitmesini engeller.
├── requirements.txt                -> Python bagimlilik listesi ve surum araliklari.
├── main.py                         -> FastAPI uygulamasini ayaga kaldiran giris noktasi; middleware ve exception handler burada.
└── README.md                       -> Backend'e ozel kurulum, calistirma ve test dokumantasyonu.
```

### Front - End

```text
Front - End/                        -> Kullanici arayuzunun gelistirildigi React tabanli frontend ana klasoru.
├── public/                         -> Build sirasinda dogrudan servis edilen statik varliklar.
│   └── favicon.svg                 -> Tarayici sekmesinde gorunen uygulama ikonu.
├── src/                            -> Uygulamanin tum kaynak kodlari.
│   ├── api/                        -> Backend ile haberlesen HTTP istemci katmani.
│   │   ├── client.js               -> Axios instance tanimi (base URL, timeout gibi genel ayarlar).
│   │   └── legalApi.js             -> PDF upload ve ajan sorgusu icin endpoint cagri fonksiyonlari.
│   ├── components/                 -> Tekrar kullanilabilir UI bilesenleri.
│   │   ├── QueryPanel.jsx          -> Soru gonderme, markdown cevap gosterimi ve sorgu hata durumlarini yonetir.
│   │   └── UploadPanel.jsx         -> Dosya secme/surukle-birak, ilerleme cubugu ve yukleme sonucunu gosterir.
│   ├── hooks/                      -> Arayuz islemleri icin ozel React hook'lari.
│   │   ├── useAgentQuery.js        -> Sorgu gonderme sureci, loading ve sonuc state yonetimi.
│   │   └── usePdfUpload.js         -> PDF yukleme sureci, progress ve hata state yonetimi.
│   ├── pages/                      -> Sayfa seviyesinde bilesen birlestirme katmani.
│   │   └── HomePage.jsx            -> UploadPanel ve QueryPanel'i ayni sayfada bir araya getirir.
│   ├── styles/                     -> Global stil ve tema tanimlari.
│   │   └── main.css                -> Fontlar, arka plan, temel tipografi ve genel stiller.
│   ├── App.jsx                     -> Uygulamanin ana bileşeni, HomePage'i render eder.
│   └── index.jsx                   -> React uygulamasinin DOM'a mount edildigi giris noktasi.
├── .env.example                    -> VITE_API_BASE_URL ve timeout gibi frontend ortam degiskenleri sablonu.
├── .gitignore                      -> node_modules, dist ve benzeri dosyalarin gite eklenmesini engeller.
├── index.html                      -> Vite'in kullandigi ana HTML sablonu ve root div'i.
├── package.json                    -> NPM bagimliliklari ve script komutlari (dev/build/preview).
├── package-lock.json               -> Kurulan paketlerin kilitli surum agaci.
├── postcss.config.js               -> Tailwind ve Autoprefixer PostCSS pipeline ayarlari.
├── tailwind.config.js              -> Tailwind tema genisletmeleri (renk, font, animasyon, shadow).
├── vite.config.js                  -> Vite gelistirme sunucusu ve plugin ayarlari.
├── dist/                           -> Uretim build ciktilarinin olustugu klasor.
├── node_modules/                   -> Frontend tarafi paketlerinin fiziksel olarak kuruldugu klasor.
└── README.md                       -> Frontend'e ozel kurulum ve kullanim dokumantasyonu.
```

### Kök Dizin
- `README.md`
	-> Projenin ana dokümantasyonu (bu dosya).
- `plan.md`
	-> Geliştirme fazları, hedef mimari ve görev takip planı.
- `.gitignore`
	-> Git'e dahil edilmeyecek dosya ve klasör tanımları.
- `Back - End/`
	-> FastAPI tabanlı sunucu, RAG ve agent akışı.
- `Front - End/`
	-> React tabanlı kullanıcı arayüzü.

### Back - End (Dosya Dosya)
- `Back - End/main.py`
	-> FastAPI uygulama giriş noktası.
	-> CORS middleware, request timing middleware, global exception handler ve `/health` endpoint burada.

- `Back - End/requirements.txt`
	-> Python bağımlılıkları (FastAPI, LangChain, LangGraph, ChromaDB, PyMuPDF vb.).

- `Back - End/.env.example`
	-> Ortam değişkeni şablonu.
	-> LM Studio bağlantısı, embedding modeli, Chroma ayarları, CORS, upload/chunk limitleri bu dosyada.

- `Back - End/.env`
	-> Çalışan ortam dosyası (yerel ayarlar).

- `Back - End/README.md`
	-> Backend'e özel kurulum ve test adımları.

- `Back - End/clear_chroma.py`
	-> Proje kökünden hızlıca Chroma dizinini silmek için kısa script.

- `Back - End/scripts/clear_chroma.py`
	-> Chroma veri klasörünü temizleyen yardımcı script (daha düzenli script klasörü altında).

- `Back - End/api/__init__.py`
	-> `api` paketini Python modülü olarak işaretler.

- `Back - End/api/routes.py`
	-> API endpoint tanımları:
	-> `POST /api/v1/document/upload` (yükle, işle, embed et, indeksle)
	-> `POST /api/v1/agent/query` (LangGraph akışını çalıştır, markdown cevap dön)
	-> Pydantic şemaları (`UploadResponse`, `QueryRequest`, `QueryResponse`).

- `Back - End/core/__init__.py`
	-> `core` paketini Python modülü olarak işaretler.

- `Back - End/core/config.py`
	-> `.env` dosyasından ayarları okur, `Settings` nesnesine toplar.
	-> Upload dizinini otomatik oluşturur.

- `Back - End/core/logger.py`
	-> Uygulama log formatını ve seviyesini merkezi şekilde ayarlar.

- `Back - End/database/__init__.py`
	-> `database` paketini Python modülü olarak işaretler.

- `Back - End/database/vector_store.py`
	-> ChromaDB wrapper katmanı.
	-> Doküman upsert, source/filename kontrolü, similarity search, keyword search, koleksiyon boyut kontrolü.
	-> Embedding boyutu uyuşmazlığında koleksiyonu yeniden oluşturup retry yapar.

- `Back - End/services/__init__.py`
	-> `services` paketini Python modülü olarak işaretler.

- `Back - End/services/pdf_processor.py`
	-> PDF dosyasını güvenli kaydetme (`save_uploaded_pdf`).
	-> PyMuPDF ile metin çıkarma (`extract_text_from_pdf`).
	-> RecursiveCharacterTextSplitter ile chunk üretme (`chunk_legal_text`).
	-> Uçtan uca ingestion helper (`ingest_pdf_to_chunks`).

- `Back - End/services/embedding.py`
	-> HuggingFace embedding modelini yükler.
	-> Doküman ve sorgu embedding fonksiyonlarını asenkron kullanıma açar.

- `Back - End/services/retrieval.py`
	-> Sorgu embedding üretimi + Chroma similarity search.
	-> Hybrid recall için keyword search birleştirmesi.
	-> Varsa CrossEncoder reranking ile sonuçları iyileştirme.

- `Back - End/agent/__init__.py`
	-> `agent` paketini Python modülü olarak işaretler.

- `Back - End/agent/graph.py`
	-> LangGraph akışının graph tanımı.
	-> `grade_documents` sonrası koşullu yönlendirme:
	-> Yetersiz sonuç varsa retrieval'a geri dön, yeterliyse generate'e geç.

- `Back - End/agent/nodes.py`
	-> Node implementasyonları:
	-> `analyze_query_node`, `retrieve_documents_node`, `grade_documents_node`, `generate_answer_node`
	-> LM Studio bağlantısı (`ChatOpenAI` OpenAI-compatible base_url ile).
	-> Prompt kuralları ve state yönetimi.

- `Back - End/data/uploads/`
	-> Yüklenen PDF dosyalarının saklandığı klasör.

- `Back - End/data/chroma/`
	-> ChromaDB kalıcı indeks verileri (local persistent storage).

- `Back - End/venv/`
	-> Backend Python sanal ortamı.

### Front - End (Dosya Dosya)
- `Front - End/package.json`
	-> Node bağımlılıkları ve script'ler (`dev`, `build`, `preview`).

- `Front - End/package-lock.json`
	-> NPM bağımlılık kilit dosyası (deterministic kurulum).

- `Front - End/.env.example`
	-> Frontend ortam değişkeni şablonu (`VITE_API_BASE_URL`, `VITE_API_TIMEOUT_MS`).

- `Front - End/.env`
	-> Frontend yerel ortam ayarları.

- `Front - End/index.html`
	-> React root (`#root`) içeren HTML giriş dosyası.

- `Front - End/vite.config.js`
	-> Vite dev server ayarları.

- `Front - End/tailwind.config.js`
	-> Tailwind tema uzantıları (renkler, fontlar, gölgeler, animasyon).

- `Front - End/postcss.config.js`
	-> PostCSS eklentileri (`tailwindcss`, `autoprefixer`).

- `Front - End/README.md`
	-> Frontend'e özel dokümantasyon.

- `Front - End/src/index.jsx`
	-> React render başlangıç noktası.

- `Front - End/src/App.jsx`
	-> Ana uygulama shell'i (HomePage render eder).

- `Front - End/src/pages/HomePage.jsx`
	-> Sayfa düzeni, UploadPanel ve QueryPanel kompozisyonu.

- `Front - End/src/components/UploadPanel.jsx`
	-> PDF sürükle-bırak, dosya seçme, upload progress ve sonuç/hata gösterimi.

- `Front - End/src/components/QueryPanel.jsx`
	-> Soru giriş alanı, sorgu butonu, markdown cevap görünümü ve meta bilgileri.

- `Front - End/src/hooks/usePdfUpload.js`
	-> Upload işleminin state yönetimi (yükleniyor, yüzde, hata, response).

- `Front - End/src/hooks/useAgentQuery.js`
	-> Agent query state yönetimi (sorgu süreci, markdown sonuç, meta, hata).

- `Front - End/src/api/client.js`
	-> Axios istemcisi (base URL ve timeout burada belirlenir).

- `Front - End/src/api/legalApi.js`
	-> Backend endpoint çağrıları (`uploadDocument`, `queryAgent`).

- `Front - End/src/styles/main.css`
	-> Global stiller, font importları, gradient arka plan ve tema sınıfları.

- `Front - End/public/favicon.svg`
	-> Tarayıcı sekmesi ikonu.

- `Front - End/dist/`
	-> Build çıktıları.

- `Front - End/node_modules/`
	-> NPM paketleri.

## Kurulum ve Çalıştırma

### 1) Ön Gereksinimler
- Python 3.9+
- Node.js 18+ (önerilir)
- npm
- LM Studio (Local Server açık olmalı)

### 2) Backend Kurulumu
```bash
cd "Back - End"

# Sanal ortam (opsiyonel ama önerilir)
python3 -m venv venv
source venv/bin/activate

# Bağımlılıklar
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Ortam değişkenleri
cp .env.example .env
```

### 3) Frontend Kurulumu
```bash
cd "Front - End"
npm install
cp .env.example .env
```

### 4) Uygulamayı Çalıştırma

Terminal-1 (Backend):
```bash
cd "Back - End"
python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Terminal-2 (Frontend):
```bash
cd "Front - End"
npm run dev -- --host 127.0.0.1 --port 5173
```

### 5) Erişim Adresleri
- Frontend -> http://127.0.0.1:5173
- Backend health -> http://127.0.0.1:8000/health
- Swagger -> http://127.0.0.1:8000/docs

## API Uç Noktaları
- `POST /api/v1/document/upload`
	-> Multipart form-data ile `file` alanında PDF bekler.
- `POST /api/v1/agent/query`
	-> JSON body ile `query` ve opsiyonel `max_attempts` alır.

Örnek query isteği:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/agent/query" \
	-H "Content-Type: application/json" \
	-d '{"query":"KVKK kapsamında açık rıza nedir?","max_attempts":2}'
```

## Konfigürasyon Notları
- Backend `.env` içindeki `LMSTUDIO_BASE_URL`, `LMSTUDIO_MODEL` ve `LMSTUDIO_API_KEY` değerleri doğru olmalıdır.
- Frontend `.env` içindeki `VITE_API_BASE_URL` backend adresiyle eşleşmelidir.
- Embedding modeli değiştirildiğinde indeks uyumsuzluğu yaşamamak için Chroma temizlenebilir:

```bash
cd "Back - End"
python3 scripts/clear_chroma.py
```

## Hızlı Sorun Giderme
- Upload sırasında hata alırsan:
	-> PDF türü/boş dosya/limit kontrolü yap.
	-> Backend loglarını incele.
- Query sırasında cevap gelmiyorsa:
	-> LM Studio Local Server açık mı kontrol et.
	-> `LMSTUDIO_BASE_URL` doğru mu kontrol et.
- Frontend backend'e ulaşamıyorsa:
	-> `VITE_API_BASE_URL` ve CORS ayarlarını kontrol et.

## Özet
Bu proje, klasik bir "PDF yükle ve cevap al" uygulamasından daha fazlasını yapar:
- Hukuki metni parçalar,
- Vektör + keyword tabanlı retrieval uygular,
- Gerekirse reranking yapar,
- LangGraph ile çok adımlı karar akışı yürütür,
- Sonucu markdown rapor olarak kullanıcıya sunar.


