import QueryPanel from "../components/QueryPanel";
import UploadPanel from "../components/UploadPanel";
import { useAgentQuery } from "../hooks/useAgentQuery";
import { usePdfUpload } from "../hooks/usePdfUpload";

export default function HomePage() {
  const { isUploading, progress, uploadInfo, uploadError, handleUpload } = usePdfUpload();
  const { isQuerying, result, meta, queryError, askQuestion } = useAgentQuery();

  return (
    <main className="min-h-screen bg-scene px-4 py-8 sm:px-6 lg:px-10">
      <div className="mx-auto max-w-7xl animate-rise">
        <header className="mb-6 rounded-2xl border border-slate-200/70 bg-white/80 p-5 shadow-soft backdrop-blur">
          <p className="font-display text-xs uppercase tracking-[0.28em] text-accent">LegalDoc Navigator</p>
          <h1 className="mt-2 font-display text-3xl text-ink sm:text-4xl">
            Hukuki Metinler Icin Agentik Analiz Konsolu
          </h1>
          <p className="mt-3 max-w-3xl text-sm text-slate-600">
            PDF yukle, vektor tabanina kaydet ve hukuki soruna kaynaklara dayali markdown rapor al.
          </p>
        </header>

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <UploadPanel
            isUploading={isUploading}
            progress={progress}
            uploadInfo={uploadInfo}
            uploadError={uploadError}
            onUpload={handleUpload}
          />
          <QueryPanel
            isQuerying={isQuerying}
            queryError={queryError}
            result={result}
            meta={meta}
            onAsk={askQuestion}
          />
        </section>
      </div>
    </main>
  );
}
