import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const apiTimeoutMs = Number(import.meta.env.VITE_API_TIMEOUT_MS || 600000);

const client = axios.create({
  baseURL,
  timeout: apiTimeoutMs,
});

export default client;
