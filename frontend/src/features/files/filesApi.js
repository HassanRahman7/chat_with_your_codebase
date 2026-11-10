import apiClient from "../../lib/apiClient";

export async function getRepositoryFiles(repositoryId, signal) {
  const response = await apiClient.get(`/repositories/${repositoryId}/files`, {
    signal,
  });
  return response.data;
}

export async function getFileContent(repositoryId, path, signal) {
  const response = await apiClient.get(
    `/repositories/${repositoryId}/files/content`,
    {
      params: { path },
      signal,
    },
  );
  return response.data;
}
