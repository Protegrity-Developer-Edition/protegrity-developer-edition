/**
 * API client for conversation management
 * Uses centralized API client for consistent error handling
 */

import { apiGet, apiPost, apiPatch, apiDelete } from './client.js';

/**
 * Fetch all active conversations (paginated)
 * @param {number} page - Page number (default: 1)
 * @param {number} pageSize - Items per page (default: 50, max: 100)
 * @returns {Promise<{count: number, next: string|null, previous: string|null, results: Array}>}
 */
export async function fetchConversations(page = 1, pageSize = 50) {
  return apiGet(`/api/conversations/?page=${page}&page_size=${pageSize}`);
}

/**
 * Fetch a single conversation with all messages
 * @param {string} id - Conversation UUID
 * @returns {Promise<{id: string, title: string, model_id: string, messages: Array, created_at: string, updated_at: string}>}
 */
export async function fetchConversation(id) {
  return apiGet(`/api/conversations/${id}/`);
}

/**
 * Create a new conversation
 * @param {{title?: string, model_id: string}} data
 * @returns {Promise<{id: string, title: string, model_id: string, messages: Array, created_at: string, updated_at: string}>}
 */
export async function createConversation(data) {
  return apiPost('/api/conversations/', data);
}

/**
 * Update a conversation (currently only title)
 * @param {string} id - Conversation UUID
 * @param {{title: string}} data
 * @returns {Promise<Object>}
 */
export async function updateConversation(id, data) {
  return apiPatch(`/api/conversations/${id}/`, data);
}

/**
 * Delete a conversation (soft delete)
 * @param {string} id - Conversation UUID
 * @returns {Promise<void>}
 */
export async function deleteConversation(id) {
  return apiDelete(`/api/conversations/${id}/`);
}

/**
 * Add a message to a conversation
 * Note: Generally you should use the chat endpoint instead
 * @param {string} conversationId - Conversation UUID
 * @param {{role: string, content: string, protegrity_data?: object}} data
 * @returns {Promise<Object>}
 */
export async function addMessage(conversationId, data) {
  return apiPost(`/api/conversations/${conversationId}/messages/`, data);
}

/**
 * Transform database conversation to app format
 * @param {Object} dbConversation - Conversation from REST API
 * @returns {Object} - Conversation in app format
 */
export function transformConversation(dbConversation) {
  const transformed = {
    id: dbConversation.id,
    title: dbConversation.title,
    messages: (dbConversation.messages || []).map((msg) => {
      return {
        role: msg.role,
        content: msg.content,
        pending: msg.pending || false,
        blocked: msg.blocked || false,
        protegrityData: msg.protegrity_data || {},
        agent: msg.agent || null,
        llm_provider: msg.llm_provider || null,
      };
    }),
    createdAt: new Date(dbConversation.created_at),
    updatedAt: new Date(dbConversation.updated_at),
  };

  return transformed;
}
