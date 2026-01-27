import { useCallback, useMemo } from "react";
import { useOpenAiGlobal } from "./useOpenAiGlobal";

export function useWidgetState(defaultState = {}) {
  const widgetState = useOpenAiGlobal("widgetState");
  const mergedState = useMemo(() => {
    if (!widgetState) {
      return { ...defaultState };
    }
    return { ...defaultState, ...widgetState };
  }, [defaultState, widgetState]);

  const setWidgetState = useCallback(
    (updater) => {
      if (typeof window === "undefined") {
        return;
      }

      const nextState =
        typeof updater === "function" ? updater(mergedState) : updater;
      if (!window.openai || typeof window.openai.setWidgetState !== "function") {
        return;
      }
      window.openai.setWidgetState(nextState);
    },
    [mergedState]
  );

  return [mergedState, setWidgetState];
}
