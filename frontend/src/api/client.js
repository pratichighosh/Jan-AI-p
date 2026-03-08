import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
});

// Add language header to all requests
client.interceptors.request.use((config) => {
  const lang = localStorage.getItem('cais_language') || 'hi';
  config.headers['Accept-Language'] = lang;
  return config;
});

export const uploadDocument = async (file, language = 'hi', documentType = null, schemeId = null) => {
  const form = new FormData();
  form.append('file', file);
  form.append('language', language);
  if (documentType) form.append('document_type', documentType);
  if (schemeId) form.append('scheme_id', schemeId);

  const { data } = await client.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getOcrResult = async (documentId) => {
  const { data } = await client.get(`/documents/${documentId}/ocr`);
  return data;
};

export const getAnalysis = async (documentId) => {
  const { data } = await client.get(`/analysis/${documentId}`);
  return data;
};

export const getProgress = async (userId) => {
  const { data } = await client.get(`/progress/${userId}`);
  return data;
};

export const markActionComplete = async (userId, documentId, actionId) => {
  const { data } = await client.post(`/progress/${userId}/${documentId}/complete/${actionId}`);
  return data;
};

export const healthCheck = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_API_URL?.replace('/api/v1', '') || 'http://localhost:8000'}/health`, { timeout: 5000 });
    return response.data;
  } catch {
    return null;
  }
};
