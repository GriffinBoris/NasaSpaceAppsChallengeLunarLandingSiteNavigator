import { onScopeDispose } from "vue";

export function usePolling(callback: (signal: AbortSignal) => Promise<void>, shouldStop: () => boolean, intervalMilliseconds: number) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let request: AbortController | null = null;

  async function poll() {
    timer = undefined;

    if (shouldStop()) {
      return;
    }

    const currentRequest = new AbortController();

    request = currentRequest;

    try {
      await callback(currentRequest.signal);
    } finally {
      if (request === currentRequest) {
        request = null;

        if (!currentRequest.signal.aborted && !shouldStop()) {
          startPolling();
        }
      }
    }
  }

  function startPolling() {
    if (timer !== undefined || request !== null || shouldStop()) {
      return;
    }

    timer = setTimeout(() => void poll(), intervalMilliseconds);
  }

  function stopPolling() {
    clearTimeout(timer);
    timer = undefined;
    request?.abort();
    request = null;
  }

  onScopeDispose(stopPolling);

  return { startPolling, stopPolling };
}
