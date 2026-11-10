import apiClient from "../../lib/apiClient";

export async function askQuestion(repositoryId, { question, conversationId } = {}) {
  const response = await apiClient.post(`/chat/${repositoryId}`, {
    question,
    conversation_id: conversationId ?? null,
  });
  return response.data;
}

export async function getConversationHistory(repositoryId, { limit = 20, offset = 0, signal } = {}) {
  const response = await apiClient.get(`/chat/${repositoryId}/history`, {
    params: { limit, offset },
    signal,
  });
  return response.data;
}

export async function getConversation(conversationId, repositoryId, signal) {
  const response = await apiClient.get(`/chat/conversations/${conversationId}`, {
    params: { repository_id: repositoryId },
    signal,
  });
  return response.data;
}

export async function deleteConversation(conversationId, repositoryId) {
  await apiClient.delete(`/chat/conversations/${conversationId}`, {
    params: { repository_id: repositoryId },
  });
}
