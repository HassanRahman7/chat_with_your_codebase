import { useCallback, useEffect, useRef, useState } from "react";

import { getRepositoryStatus } from "../features/indexing/indexingApi";
import { isActiveStatus } from "../features/indexing/statusLabels";
import { getRepository } from "../features/repositories/repositoriesApi";

const INITIAL_STATE = {
  repository: null,
  status: null,
  state: "loading",
  error: null,
};

export function useRepositoryStatus(repositoryId) {
  const [data, setData] = useState(INITIAL_STATE);
  const controllerRef = useRef(null);

  const load = useCallback(
    async ({ silent = false } = {}) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;

      if (!silent) {
        setData((previous) => ({
          ...previous,
          state: previous.repository ? "refreshing" : "loading",
          error: null,
        }));
      }

      try {
        const [repository, status] = await Promise.all([
          getRepository(repositoryId, controller.signal),
          getRepositoryStatus(repositoryId, controller.signal),
        ]);
        setData({
          repository,
          status,
          state: "ready",
          error: null,
        });
      } catch (error) {
        if (error?.cancelled) return;
        setData((previous) => ({
          ...previous,
          state: "error",
          error,
        }));
      }
    },
    [repositoryId],
  );

  useEffect(() => {
    load();
    return () => controllerRef.current?.abort();
  }, [load]);

  const active = isActiveStatus(data.status?.repository_status);
  useEffect(() => {
    if (!active) return undefined;
    const timer = window.setTimeout(() => load({ silent: true }), 2500);
    return () => window.clearTimeout(timer);
  }, [active, data.status, load]);

  const refresh = useCallback(() => load({ silent: true }), [load]);

  return { ...data, refresh };
}
