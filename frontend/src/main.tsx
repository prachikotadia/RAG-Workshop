import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import { ThemeProvider } from './contexts/ThemeContext';
import './styles/globals.css';

// Clear any old service workers and caches on app load
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    registrations.forEach((registration) => {
      registration.unregister();
    });
  });
}

if ('caches' in window) {
  caches.keys().then((names) => {
    names.forEach((name) => {
      caches.delete(name);
    });
  });
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <RouterProvider router={router} />
    </ThemeProvider>
  </React.StrictMode>
);

