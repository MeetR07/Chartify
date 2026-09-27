import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Generate a unique device ID and inject it into all fetch requests
if (!localStorage.getItem('chartify_device_id')) {
  localStorage.setItem('chartify_device_id', crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2));
}

const originalFetch = window.fetch;
window.fetch = async (resource, config = {}) => {
  const deviceId = localStorage.getItem('chartify_device_id');
  if (resource instanceof Request) {
    resource.headers.set('X-Device-Id', deviceId);
  } else {
    if (!config.headers) {
      config.headers = {};
    }
    if (config.headers instanceof Headers) {
      config.headers.set('X-Device-Id', deviceId);
    } else {
      config.headers['X-Device-Id'] = deviceId;
    }
  }
  return originalFetch(resource, config);
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
