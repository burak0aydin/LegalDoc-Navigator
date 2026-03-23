import shutil
from pathlib import Path

chroma_dir = Path("./data/chroma")
if chroma_dir.exists() and chroma_dir.is_dir():
    shutil.rmtree(chroma_dir)
    print("Mevcut chroma veritabani temizlendi.")
else:
    print("Silinecek veritabani bulunamadi.")
