import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function QueryPanel({ isQuerying, queryError, result, meta, onAsk }) {
  const [query, setQuery] = useState("");

  const onSubmit = async (event) => {
    event.preventDefault();
    await onAsk(query);
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-soft backdrop-blur">
      <p className="font-display text-xs uppercase tracking-[0.24em] text-accent">Ajan Iletisimi</p>
      <h2 className="mt-2 font-display text-2xl text-ink">Hukuki Soru Sor</h2>

      <form onSubmit={onSubmit} className="mt-5 space-y-3">
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="min-h-28 w-full rounded-xl border border-slate-300 bg-white p-3 text-sm outline-none ring-accent/30 focus:ring"
          placeholder="Ornek: Is sozlesmesinin tek tarafli feshi durumunda isverenin yukumlulukleri nelerdir?"
        />
        <button
          type="submit"
          disabled={isQuerying}
          className="rounded-lg bg-ember px-4 py-2 font-display text-sm text-white transition hover:bg-ember/90 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {isQuerying ? "Ajan dusunuyor..." : "Rapor Uret"}
        </button>
      </form>

      {queryError ? (
        <p className="mt-4 rounded-lg border border-rose-300 bg-rose-50 p-3 text-sm text-rose-700">{queryError}</p>
      ) : null}

      <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="font-display text-xs uppercase tracking-[0.16em] text-slate-500">Markdown Rapor</p>
        {result ? (
          <article className="prose prose-sm mt-3 max-w-none prose-headings:font-display prose-p:font-body prose-li:font-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result}</ReactMarkdown>
          </article>
        ) : (
          <p className="mt-3 text-sm text-slate-500">Rapor burada görüntülenecek.</p>
        )}
      </div>

      {meta ? (
        <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-slate-600 sm:grid-cols-3">
          <span className="rounded bg-slate-100 px-2 py-1">Deneme: {meta.attempts}</span>
          <span className="rounded bg-slate-100 px-2 py-1">İlgili kaynak: {meta.relevant_results_count}</span>
          <span className="rounded bg-slate-100 px-2 py-1">Hata kaydı: {meta.errors?.length ?? 0}</span>
        </div>
      ) : null}
    </section>
  );
}
