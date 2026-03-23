import { useCallback, useState } from "react";
import { queryAgent } from "../api/legalApi";

export function useAgentQuery() {
  const [isQuerying, setIsQuerying] = useState(false);
  const [result, setResult] = useState("");
  const [meta, setMeta] = useState(null);
  const [queryError, setQueryError] = useState("");

  const askQuestion = useCallback(async (queryText) => {
    setQueryError("");

    if (!queryText || queryText.trim().length < 3) {
      setQueryError("Lutfen en az 3 karakterlik bir hukuki soru yazin.");
      return null;
    }

    setIsQuerying(true);
    try {
      const data = await queryAgent(queryText.trim(), 2);
      setResult(data.answer_markdown || "");
      setMeta(data);
      return data;
    } catch (error) {
      const detail = error?.response?.data?.detail || "Sorgu sirasinda hata olustu.";
      setQueryError(String(detail));
      return null;
    } finally {
      setIsQuerying(false);
    }
  }, []);

  return {
    isQuerying,
    result,
    meta,
    queryError,
    askQuestion,
  };
}
