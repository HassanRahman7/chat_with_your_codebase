import apiClient from "../../lib/apiClient";

export async function createRepository(githubUrl) {
  const response = await apiClient.post("/repositories", {
    github_url: githubUrl,
  });
  return response.data;
}

export async function listRepositories({ limit = 10, offset = 0, signal } = {}) {
  const response = await apiClient.get("/repositories", {
    params: { limit, offset },
    signal,
  });
  return response.data;
}

export async function getRepository(repositoryId, signal) {
  const response = await apiClient.get(`/repositories/${repositoryId}`, {
    signal,
  });
  return response.data;
}

export async function deleteRepository(repositoryId) {
  await apiClient.delete(`/repositories/${repositoryId}`);
}

export async function startIndexing(repositoryId, { force = false } = {}) {
  const response = await apiClient.post(`/repositories/${repositoryId}/index`, {
    force,
  });
  return response.data;
}
