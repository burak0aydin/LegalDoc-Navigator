# LegalDoc Navigator - Detaylı Geliştirme ve Mimari Planı

Bu belge, "LegalDoc Navigator" projesinin tam kapsamlı sistem mimarisini, klasör yapısını ve adım adım uygulama adımlarını tanımlar. Geliştirme asistanı (AI), bu adımları sırayla okuyacak, her aşamadaki görevleri eksiksiz yerine getirecek ve bir sonraki aşamaya geçmeden önce kullanıcıdan onay alacaktır.

---

## 🏗️ 1. Hedeflenen Sistem Mimarisi ve Klasör Yapısı

Proje, birbirlerinden bağımsız (decoupled) çalışabilen, RESTful API üzerinden haberleşen iki ana modülden oluşacaktır. Klasör isimlendirmeleri tam olarak aşağıdaki gibi olmalıdır:

```text
LegalDoc-Navigator/
├── Back - End/
│   ├── api/                    # FastAPI route'ları ve endpoint tanımları
│   │   ├── __init__.py
│   │   ├── routes.py           # /yukle, /sorgula endpoint'leri
│   ├── core/                   # Ortak ayarlar, config ve loglama işlemleri
│   │   ├── config.py           # Ortam değişkenleri (.env) yükleme
│   │   ├── logger.py           # Hata ve bilgi loglama altyapısı
│   ├── data/                   # Geçici dosya okuma/yazma (I/O) ve yüklenen PDF'ler
│   ├── database/               # Vektör veritabanı (ChromaDB/FAISS) bağlantıları
│   │   ├── vector_store.py
│   ├── services/               # İş mantığı ve RAG/Agent servisleri
│   │   ├── pdf_processor.py    # PDF okuma, temizleme ve parçalama (chunking)
│   │   ├── embedding.py        # Metinleri vektörlere dönüştürme
│   │   ├── retrieval.py        # Vektör araması ve yeniden sıralama (Reranking)
│   ├── agent/                  # LangGraph tabanlı AI iş akışı
│   │   ├── graph.py            # LangGraph düğüm (node) ve kenar (edge) tanımları
│   │   ├── nodes.py            # Agent'ın yapacağı özel görevler (Sentez, Filtreleme)
│   ├── .env.example            # Gerekli API anahtarlarının şablonu
│   ├── requirements.txt        # Python bağımlılıkları
│   ├── main.py                 # FastAPI uygulamasının başlatılacağı ana dosya
│   └── README.md               # Backend mimarisi ve kurulum talimatları
├── Front - End/
│   ├── public/                 # Statik dosyalar (ikonlar, logolar)
│   ├── src/
│   │   ├── api/                # Backend API'sine yapılan istekleri yöneten servisler
│   │   ├── components/         # Tekrar kullanılabilir UI bileşenleri (UploadBox, ChatBubble)
│   │   ├── pages/              # Ana sayfalar (Ana Ekran, Sonuç/Rapor Ekranı)
│   │   ├── hooks/              # Özel React hook'ları (örn: usePdfUpload)
│   │   ├── styles/             # Global CSS ve Tailwind ayarları
│   │   ├── App.jsx             # Ana React bileşeni
│   │   ├── index.jsx           # React render noktası
│   ├── package.json            # Node.js bağımlılıkları
│   └── README.md               # Frontend mimarisi ve çalıştırma talimatları
├── .gitignore                  # Git'e dahil edilmeyecek dosyalar (venv, node_modules, .env)
├── plan.md                     # Bu dosya
└── README.md                   # Projenin genel özeti, ekip bilgileri ve vizyonu

🛠️ 2. Adım Adım Geliştirme Aşamaları (Phases)
Asistan, aşağıdaki aşamaları sırayla takip edecektir. Her [ ] işareti bir görevi temsil eder. Görev tamamlandığında kullanıcıya bilgi verilecek ve diğer faza geçiş izni beklenecektir.

Aşama 1: Temel Kurulum ve İskeletin Oluşturulması (Phase 1)
[x] Kök dizindeki README.md dosyasının projenin vizyonu ve geliştirici ekibe (Burak Aydın, Sedef Gizem Orulluoğlu, Mert Acar) uygun şekilde güncellenmesi.

[x] Belirtilen dizin ağacına uygun olarak Back - End ve Front - End klasörlerinin, alt klasörleriyle birlikte eksiksiz oluşturulması.

[x] Back - End klasörü içinde Python sanal ortamının (venv) kuruluma hazır hale getirilmesi için dökümantasyon yazılması.

[x] Back - End/requirements.txt dosyasının oluşturulması (FastAPI, uvicorn, pydantic, langchain, langgraph, pymupdf, chromadb, python-dotenv eklenecek).

[x] Hassas verilerin korunması için kök dizin ve alt klasörlere uygun .gitignore dosyalarının eklenmesi.

Aşama 2: Veri Okuma, Yazma (I/O) ve PDF İşleme (Phase 2 - Backend)
[x] Back - End/services/pdf_processor.py dosyasında, kullanıcıdan gelen PDF dosyalarını data/ klasörüne güvenli bir şekilde kaydedecek (Dosya Yazma) asenkron fonksiyonların yazılması.

[x] Kaydedilen PDF dosyalarını PyMuPDF (fitz) kullanarak metne dökecek (Dosya Okuma) fonksiyonun yazılması.

[x] Çıkarılan ham metinlerin hukuki bağlamı koparmamak adına LangChain RecursiveCharacterTextSplitter kullanılarak anlamlı metin parçacıklarına (chunks) ayrılması. Metin örtüşme (overlap) oranının hukuki maddelerin bölünmesini engelleyecek şekilde ayarlanması.

Aşama 3: Vektör Veritabanı ve Gelişmiş Geri Getirme (RAG) (Phase 3 - Backend)
[x] Back - End/services/embedding.py içinde, parçalanan metinleri sayısal vektörlere dönüştürecek (örn: OpenAI text-embedding-3-small veya açık kaynaklı bir model) fonksiyonun yazılması.

[x] Back - End/database/vector_store.py içinde ChromaDB (veya FAISS) bağlantısının kurulması ve oluşturulan vektörlerin kalıcı (persistent) olarak veritabanına kaydedilmesi.

[x] Back - End/services/retrieval.py içinde, kullanıcının sorgusunu alıp vektör veritabanında "Semantik Arama (Similarity Search)" yapacak fonksiyonun oluşturulması.

[x] Gelişmiş Adım: Bulunan belgelerin doğruluğunu artırmak için arama sonuçlarına "Yeniden Sıralama (Cross-Encoder Reranking)" algoritmasının eklenmesi.

Aşama 4: LangGraph ile Karar Verici Yapay Zeka (Agentic Workflow) (Phase 4 - Backend)
[x] Back - End/agent/nodes.py dosyasında iş akışını yönetecek şu fonksiyonların (düğümlerin) yazılması:

Sorgu Analizi (Analyze Query): Kullanıcının sorusunun hukuki bağlamını anlama.

Belge Getirme (Retrieve): RAG servisini tetikleyerek ilgili maddeleri bulma.

Alaka Düzeyi Filtreleme (Grade Documents): Bulunan belgelerin gerçekten soruyu cevaplayıp cevaplamadığını LLM ile kontrol etme.

Yanıt Sentezleme (Generate): Geçerli belgelere dayanarak hukuki özet raporu oluşturma.

[x] Back - End/agent/graph.py dosyasında LangGraph kullanılarak bu düğümlerin birbirine bağlanması ve yönlendirme (conditional routing) mantığının kurulması (Örn: Belgeler yetersizse aramayı genişlet).

Aşama 5: FastAPI ve API Uç Noktalarının Entegrasyonu (Phase 5 - Backend)
[x] Back - End/main.py dosyasında FastAPI uygulamasının başlatılması ve CORS (Cross-Origin Resource Sharing) middleware ayarlarının yapılması (Frontend'in iletişim kurabilmesi için).

[x] Back - End/api/routes.py içinde şu iki temel endpoint'in oluşturulması:

POST /api/v1/document/upload: PDF alır, işler, vektör tabanına yazar ve başarı durumu döner.

POST /api/v1/agent/query: Kullanıcıdan gelen metin tabanlı soruyu alır, LangGraph ajanını tetikler ve Markdown formatında detaylı sonuç döner.

[x] Try-Catch bloklarıyla kapsamlı hata yönetimi (Error Handling) yapılması (Örn: PDF okunamadı, veritabanına bağlanılamadı hataları için 400 ve 500 dönülmesi).

Aşama 6: Modern Kullanıcı Arayüzü (Phase 6 - Frontend)
[x] Front - End dizininde React ve Vite (veya Next.js) tabanlı modern bir altyapının kurulması. TailwindCSS'in dahil edilmesi.

[x] Sayfanın iki ana panele bölünmesi:

Sol Panel (Doküman Yönetimi): Kullanıcının PDF dosyalarını sürükleyip bırakabileceği (Drag & Drop), okuma/yazma ilerlemesini (Progress Bar) gösteren alan.

Sağ Panel (Ajan İletişim ve Raporlama): Kullanıcının hukuki sorusunu yazabileceği chat alanı ve sistemin Markdown olarak döndüğü özet raporun (maddeler, bold vurgular dahil) görüntüleneceği alan.

[x] src/api/ klasörü içinde Axios veya Fetch API kullanılarak backend'e istek atacak asenkron servis bağlantılarının yazılması.

Aşama 7: Uçtan Uca Test ve Final Dokümantasyonu (Phase 7)
[x] Backend ve Frontend sunucularının eşzamanlı çalıştırılması.

[x] Örnek bir hukuki PDF yüklenerek (örneğin KVKK metni veya örnek bir sözleşme) baştan sona (End-to-End) sistemin test edilmesi.

[x] Yanıt sürelerinin ve agent'ın karar alma (graph routing) doğruluğunun loglardan incelenmesi.

[x] Kök dizin, Back - End ve Front - End altındaki tüm README.md dosyalarının, projenin son çalışan haline göre güncellenmesi ve kurulum komutlarının belgelenmesi.




