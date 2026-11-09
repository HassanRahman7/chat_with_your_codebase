import { useCallback, useEffect, useRef, useState } from "react";

import { listRepositories } from "../features/repositories/repositoriesApi";
import { isActiveStatus } from "../features/indexing/statusLabels";

const INITIAL_STATE = {
  items: [],
  pagination: { limit: 10, offset: 0, total: 0, has_more: false },
  state: "loading",
  error: null,
};

export function useRepositories({ limit = 10, offset = 0 } = {}) {
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
          state: previous.items.length ? "refreshing" : "loading",
          error: null,
        }));
      }

      try {
        const body = await listRepositories({
          limit,
          offset,
          signal: controller.signal,
        });
        setData({
          items: body.items,
          pagination: body.pagination,
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
    [limit, offset],
  );

  useEffect(() => {
    load();
    return () => controllerRef.current?.abort();
  }, [load]);

  const hasActiveJobs = data.items.some((item) => isActiveStatus(item.status));
  useEffect(() => {
    if (!hasActiveJobs) return undefined;
    const timer = window.setTimeout(() => load({ silent: true }), 4000);
    return () => window.clearTimeout(timer);
  }, [hasActiveJobs, data.items, load]);

  const refresh = useCallback(() => load({ silent: true }), [load]);

  return { ...data, refresh };
}
