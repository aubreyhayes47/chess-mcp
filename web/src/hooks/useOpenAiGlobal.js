import { useSyncExternalStore } from "react";

const POLL_INTERVAL_MS = 250;

const getOpenAiSnapshot = (key) => {
  if (typeof window === "undefined") {
    return undefined;
  }
  return window.openai ? window.openai[key] : undefined;
};

const subscribeToOpenAi = (callback) => {
  if (typeof window === "undefined" || !window.openai) {
    const intervalId = setInterval(callback, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }

  const openai = window.openai;
  if (typeof openai.subscribe === "function") {
    return openai.subscribe(callback);
  }
  if (typeof openai.addEventListener === "function") {
    openai.addEventListener("statechange", callback);
    return () => openai.removeEventListener("statechange", callback);
  }
  if (typeof openai.on === "function") {
    openai.on("statechange", callback);
    return () => {
      if (typeof openai.off === "function") {
        openai.off("statechange", callback);
      }
    };
  }

  const intervalId = setInterval(callback, POLL_INTERVAL_MS);
  return () => clearInterval(intervalId);
};

export function useOpenAiGlobal(key) {
  return useSyncExternalStore(
    subscribeToOpenAi,
    () => getOpenAiSnapshot(key),
    () => undefined
  );
}
