# ⚖️ LegalDoc Navigator: Hukuk Metni Analiz Agent'ı

## 📖 Proje Özeti
**LegalDoc Navigator**, uzun mevzuat metinlerinden, mahkeme kararlarından ve hukuki sözleşmelerden ilgili maddeleri hızla bulmak ve özet raporlar çıkarmak için tasarlanmış, yapay zeka destekli bir analiz ajanıdır. Kullanıcı dostu web arayüzü sayesinde karmaşık hukuki belgeler saniyeler içinde işlenir, analiz edilir ve anlaşılır hale getirilir.

## ✨ Temel Özellikler
- **PDF Parsing:** Uzun ve karmaşık hukuki PDF belgelerini okur ve işlenebilir metin parçalarına böler.
- **Akıllı Arama (RAG):** RAG (Retrieval-Augmented Generation) mimarisi ile belgeler içinde anlamsal (semantik) arama yapar.
- **Reranking:** Bulunan metin parçalarını alaka düzeyine göre yeniden sıralayarak en doğru bağlamı yakalar.
- **Agentik Analiz (LangGraph):** LangGraph tabanlı iş akışı ile hukuki metinleri yorumlar ve kullanıcının sorusuna özel, net özet raporlar oluşturur.
- **Web Arayüzü:** Kullanıcıların kolayca belge yükleyip sonuçları görüntüleyebileceği modern bir önyüz.

## 🛠️ Kullanılan Teknolojiler

### Backend (Yapay Zeka & Veri İşleme)
- **PDF İşleme:** PyMuPDF / pdfplumber / Unstructured
- **Vektör Veritabanı:** ChromaDB / FAISS / Qdrant
- **Arama & Optimizasyon:** RAG Pipeline & Cross-Encoder Reranking modelleri
- **Orkestrasyon:** LangGraph & LangChain
- **API:** FastAPI / Flask

### Frontend (Kullanıcı Arayüzü)
- **Web Çerçevesi:** React / Vue.js / Streamlit (Proje gereksinimine göre güncellenecektir)
- **İletişim:** REST API entegrasyonu

## ⚙️ Sistem Mimarisi ve Çalışma Mantığı
1. **Yükleme:** Kullanıcı web arayüzü üzerinden incelemek istediği hukuki PDF belgesini sisteme yükler.
2. **İşleme (Parsing):** Sistem PDF'i metne dönüştürür ve anlam bütünlüğünü koruyarak parçalara (chunk) ayırır.
3. **Vektörizasyon:** Metin parçaları embedding modelleri ile vektörlere dönüştürülüp veritabanına kaydedilir.
4. **Sorgulama ve RAG:** Kullanıcı bir soru sorduğunda, sistem en alakalı parçaları bulur (Retrieval).
5. **Reranking:** Bulunan parçalar alaka düzeyine göre çapraz kodlayıcılar ile yeniden sıralanır.
6. **Sentez ve Raporlama:** LangGraph ajanları en doğru bilgileri derler ve LLM aracılığıyla kullanıcıya özet bir rapor sunar.

## 🚀 Kurulum ve Çalıştırma

### Ön Koşullar
- Python 3.9+
- Node.js (Frontend için)

### Adımlar

```bash
# 1. Repoyu klonlayın
git clone [https://github.com/kullanici-adi/LegalDoc-Navigator.git](https://github.com/kullanici-adi/LegalDoc-Navigator.git)
cd LegalDoc-Navigator

# 2. Sanal ortam oluşturun ve aktif edin
python -m venv venv
source venv/bin/activate  # Windows için: venv\Scripts\activate

# 3. Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt

# 4. Çevresel değişkenleri ayarlayın
cp .env.example .env
# .env dosyasına gerekli API anahtarlarını ekleyin

# 5. Backend uygulamasını başlatın
uvicorn main:app --reload

# 6. Frontend'i başlatın (Ayrı bir terminalde)
cd frontend
npm install
npm start
```

##👥 Geliştirici Ekip
Bu proje aşağıdaki ekip üyeleri tarafından geliştirilmektedir:

- **Burak Aydın - 1911012833

- **Sedef Gizem Orulluoğlu - 2211012047

- **Mert Acar - 2311012072


