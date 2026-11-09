import { useCallback, useEffect, useRef, useState } from "react";

import { getSystemHealth } from "../features/system/healthApi";

const INITIAL_STATE = {
  state: "loading",
  data: null,
  error: null,
  checkedAt: null,
};

/**
 * Load real backend health. No simulated states or timers: the UI renders
 * exactly what the API reports.
 */
export function useSystemHealth() {
  const [health, setHealth] = useState(INITIAL_STATE);
  const controllerRef = useRef(null);

  const refresh = useCallback(async () => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setHealth((previous) => ({
      ...previous,
      state: previous.data ? "refreshing" : "loading",
      error: null,
    }));

    try {
      const data = await getSystemHealth(controller.signal);
      setHealth({
        state: data.httpStatus === 200 ? "online" : "degraded",
        data,
        error: null,
        checkedAt: new Date(),
      });
    } catch (error) {
      if (error?.cancelled) return;
      setHealth({
        state: "offline",
        data: null,
        error,
        checkedAt: new Date(),
      });
    }
  }, []);

  useEffect(() => {
    refresh();
    return () => controllerRef.current?.abort();
  }, [refresh]);

  return { ...health, refresh };
}
