import { useCallback, useState } from "react";
import { uploadDocument } from "../api/legalApi";

export function usePdfUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadInfo, setUploadInfo] = useState(null);
  const [uploadError, setUploadError] = useState("");

  const handleUpload = useCallback(async (file) => {
    setUploadError("");
    setUploadInfo(null);
    setProgress(0);

    if (!file) {
      setUploadError("Lutfen bir PDF secin.");
      return null;
    }

    if (file.type !== "application/pdf") {
      setUploadError("Sadece PDF dosyasi yuklenebilir.");
      return null;
    }

    setIsUploading(true);
    try {
      const data = await uploadDocument(file, setProgress);
      setUploadInfo(data);
      setProgress(100);
      return data;
    } catch (error) {
      const detail = error?.response?.data?.detail
        || error?.response?.data?.message
        || error?.response?.data?.error
        || error?.message
        || (error?.request ? "Sunucuya ulasilamadi. Backend calisiyor mu ve CORS ayari dogru mu kontrol edin." : null)
        || "Yukleme sirasinda hata olustu.";
      setUploadError(String(detail));
      return null;
    } finally {
      setIsUploading(false);
    }
  }, []);

  return {
    isUploading,
    progress,
    uploadInfo,
    uploadError,
    handleUpload,
  };
}
