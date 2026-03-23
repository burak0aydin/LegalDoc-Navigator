import client from "./client";

export async function uploadDocument(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await client.post("/api/v1/document/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (!event.total || !onProgress) {
        return;
      }
      const percent = Math.round((event.loaded * 100) / event.total);
      onProgress(percent);
    },
  });

  return response.data;
}

export async function queryAgent(query, maxAttempts = 2) {
  const response = await client.post("/api/v1/agent/query", {
    query,
    max_attempts: maxAttempts,
  });

  return response.data;
}
