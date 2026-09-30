"use client";

import { useCallback, useState } from "react";

/**
 * Like useState, but mirrors the value to localStorage under `key`
 * (per-project keys are built by the caller). Booleans are stored as
 * "true"/"false"; anything else is stored via String().
 */
export function usePersistedState<T extends string | boolean>(
  key: string,
  defaultValue: T,
): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const saved = localStorage.getItem(key);
      if (saved === null) return defaultValue;
      if (typeof defaultValue === "boolean") return (saved === "true") as T;
      return saved as T;
    } catch {
      return defaultValue;
    }
  });

  const set = useCallback(
    (next: T) => {
      setValue(next);
      try {
        localStorage.setItem(key, String(next));
      } catch {
        // localStorage unavailable (private mode, quota) — state still updates
      }
    },
    [key],
  );

  return [value, set];
}
