/**
 * Runtime environment configuration
 *
 * This module provides environment variables that can be injected at runtime.
 * During development, it uses Vite's import.meta.env.
 * In production (Docker/CDN), it reads from window.__RUNTIME_CONFIG__.
 */

// Extend Window interface for TypeScript
declare global {
  interface Window {
    __RUNTIME_CONFIG__?: {
      API_URL: string;
      API_ACCESS_KEY?: string;  // Optional: only used in local dev, CloudFront injects in prod
      MAPBOX_TOKEN: string;
      GITHUB_REPO_URL: string;
    };
  }
}

// Get environment variables from runtime config or Vite env
const getRuntimeConfig = () => {
  // In production with CDN, config.js sets window.__RUNTIME_CONFIG__
  if (typeof window !== 'undefined' && window.__RUNTIME_CONFIG__) {
    return window.__RUNTIME_CONFIG__;
  }

  // Fallback to Vite environment variables (development)
  return {
    API_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
    API_ACCESS_KEY: import.meta.env.VITE_API_ACCESS_KEY || 'dev-insecure-key-change-in-prod',
    MAPBOX_TOKEN: import.meta.env.VITE_MAPBOX_TOKEN || '',
    GITHUB_REPO_URL: import.meta.env.VITE_GITHUB_REPO_URL || 'https://github.com/sdp5/green-gov-rag',
  };
};

export const ENV = getRuntimeConfig();

// Helper to check if we're in development mode
export const isDevelopment = import.meta.env.DEV;

// Helper to check if we're in production mode
export const isProduction = import.meta.env.PROD;

// Export individual values for convenience
export const API_URL = ENV.API_URL;
// API_ACCESS_KEY is only used in local dev (CloudFront/Front Door inject header in production)
export const API_ACCESS_KEY = ENV.API_ACCESS_KEY;
export const MAPBOX_TOKEN = ENV.MAPBOX_TOKEN;
export const GITHUB_REPO_URL = ENV.GITHUB_REPO_URL;
