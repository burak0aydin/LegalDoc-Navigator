import { useRef } from "react";

export default function UploadPanel({
  isUploading,
  progress,
  uploadInfo,
  uploadError,
  onUpload,
}) {
  const inputRef = useRef(null);

  const handleDrop = async (event) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) {
      await onUpload(file);
    }
  };

  const handleFileSelection = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      await onUpload(file);
    }
    event.target.value = "";
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-soft backdrop-blur">
      <p className="font-display text-xs uppercase tracking-[0.24em] text-accent">Dokuman Yonetimi</p>
      <h2 className="mt-2 font-display text-2xl text-ink">PDF Yukle ve Indeksle</h2>
      <p className="mt-2 text-sm text-slate-600">
        Mevzuat, karar veya sozlesme dosyasini surukleyip birak. Sistem dosyayi parcalayip vektor tabanina yazacak.
      </p>

      <div
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
        className="mt-6 rounded-xl border-2 border-dashed border-accent/40 bg-parchment p-6 text-center"
      >
        <p className="font-display text-sm text-slate-700">PDF dosyasini buraya birak</p>
        <p className="mt-1 text-xs text-slate-500">veya dosya sec butonunu kullan</p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-4 rounded-lg bg-accent px-4 py-2 font-display text-sm text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:bg-slate-300"
          disabled={isUploading}
        >
          {isUploading ? "Yukleniyor..." : "Dosya Sec"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          onChange={handleFileSelection}
          className="hidden"
        />
      </div>

      <div className="mt-6">
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
          <div
            className="h-full rounded-full bg-ember transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="mt-2 text-xs font-medium text-slate-600">Yukleme ilerlemesi: %{progress}</p>
      </div>

      {uploadError ? (
        <p className="mt-4 rounded-lg border border-rose-300 bg-rose-50 p-3 text-sm text-rose-700">{uploadError}</p>
      ) : null}

      {uploadInfo ? (
        <div className="mt-4 rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800">
          <p className="font-semibold">{uploadInfo.message}</p>
          <p className="mt-1">Chunk sayisi: {uploadInfo.chunks_count}</p>
        </div>
      ) : null}
    </section>
  );
}
