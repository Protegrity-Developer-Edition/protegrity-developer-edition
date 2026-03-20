// frontend/console/src/api/client.js

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

/**
 * Token management helpers
 */
export function setAccessToken(token) {
  if (token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  }
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setRefreshToken(token) {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/**
 * Centralized API fetch with authentication and error handling.
 * 
 * @param {string} path - API path (e.g., "/api/chat/")
 * @param {object} options - Fetch options
 * @returns {Promise<object>} - Response data
 * @throws {Error} - Enhanced error with code, message, status, and raw data
 */
export async function apiFetch(path, options = {}) {
  const token = getAccessToken();

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const res = await fetch(url, { ...options, headers });
  
  let data;
  try {
    data = await res.json();
  } catch {
    data = { detail: res.statusText };
  }

  if (!res.ok) {
    // Parse backend error structure
    const errorInfo = data?.error || {};
    const code = errorInfo.code || "error";
    const message = 
      errorInfo.message || 
      data?.detail || 
      res.statusText || 
      "Request failed";
    
    // Create enhanced error object
    const error = new Error(message);
    error.code = code;
    error.httpStatus = res.status;
    error.raw = data;

    // If unauthorized, clear token so App knows user is logged out
    if (res.status === 401) {
      clearTokens();
    }
    
    throw error;
  }

  return data;
}

/**
 * HTTP method helpers using apiFetch
 */
export async function apiGet(path) {
  return apiFetch(path, { method: "GET" });
}

export async function apiPost(path, body) {
  return apiFetch(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function apiPatch(path, body) {
  return apiFetch(path, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function apiDelete(path) {
  return apiFetch(path, { method: "DELETE" });
}

/**
 * Health check API
 * GET /api/health/
 */
export async function fetchHealth() {
  return apiGet("/api/health/");
}

/**
 * Chat API
 * POST /api/chat/
 * body: { conversation_id?, message, model_id?, agent_id?, protegrity_mode? }
 */
export async function sendChatMessage({ conversationId, message, modelId, agentId, protegrityMode }) {
  const payload = {
    message,
  };

  // Always send conversation_id if provided
  if (conversationId) {
    payload.conversation_id = conversationId;
  }

  // Always send model_id and agent_id if provided (allows switching mid-conversation)
  if (modelId) payload.model_id = modelId;
  if (agentId) payload.agent_id = agentId;

  // Always include protegrity_mode if specified
  if (protegrityMode) {
    payload.protegrity_mode = protegrityMode;
  }

  return apiPost("/api/chat/", payload);
}

/**
 * Poll for Fin AI response
 * GET /api/chat/poll/<conversation_id>/
 */
export async function pollConversation(conversationId) {
  return apiGet(`/api/chat/poll/${conversationId}/`);
}

/**
 * Authentication API
 * POST /api/auth/token/
 * Login with username and password to get JWT tokens
 */
export async function login({ username, password }) {
  // Don't use apiFetch here since we don't want auth headers for login
  const res = await fetch(`${API_BASE_URL}/api/auth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  let data;
  try {
    data = await res.json();
  } catch {
    data = {};
  }

  if (!res.ok) {
    const msg =
      data?.detail ||
      data?.error?.message ||
      "Login failed. Check your username and password.";
    const err = new Error(msg);
    err.code = "login_failed";
    err.httpStatus = res.status;
    throw err;
  }

  // Expecting { access: "...", refresh: "..." }
  return data;
}

/**
 * Get current authenticated user information
 * GET /api/me/
 * Returns: { id, username, email, first_name, last_name, role, is_protegrity }
 */
export async function getCurrentUser() {
  return apiGet("/api/me/");
}
