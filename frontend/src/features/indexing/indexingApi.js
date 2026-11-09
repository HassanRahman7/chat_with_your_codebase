import apiClient from "../../lib/apiClient";

export async function getRepositoryStatus(repositoryId, signal) {
  const response = await apiClient.get(
    `/repositories/${repositoryId}/status`,
    { signal },
  );
  return response.data;
}
