import { onScopeDispose, ref, watch } from "vue";
import type { LunarFeatureInterface } from "@/types/terrain/LunarFeatureInterface";
import { api } from "@/utils/api";
import { getFirstApiErrorMessage } from "@/utils/errorHandling";

export function useFeatureSearch() {
  const query = ref("");
  const features = ref<LunarFeatureInterface[]>([]);
  const catalogLoaded = ref<boolean | null>(null);
  const isLoading = ref(false);
  const hasSearched = ref(false);
  const errorMessage = ref("");
  let request: AbortController | null = null;
  let timer: ReturnType<typeof setTimeout> | undefined;

  function clear() {
    clearTimeout(timer);
    request?.abort();
    request = null;
    features.value = [];
    isLoading.value = false;
    hasSearched.value = false;
    errorMessage.value = "";
  }

  async function search() {
    clear();

    const searchQuery = query.value.trim();
    const currentRequest = new AbortController();

    request = currentRequest;
    isLoading.value = true;

    try {
      const result = await api.features.search(searchQuery, currentRequest.signal);

      if (currentRequest.signal.aborted) {
        return;
      }

      features.value = result.features;
      catalogLoaded.value = result.catalogLoaded;
      hasSearched.value = searchQuery.length > 0;
    } catch (error) {
      if (!currentRequest.signal.aborted) {
        errorMessage.value = getFirstApiErrorMessage(error, "Unable to search lunar features.");
      }
    } finally {
      if (request === currentRequest) {
        request = null;
        isLoading.value = false;
      }
    }
  }

  watch(
    query,
    (value) => {
      clear();

      if (value.trim().length < 2) {
        return;
      }

      isLoading.value = true;
      timer = setTimeout(() => void search(), 250);
    },
    { flush: "sync" }
  );
  onScopeDispose(clear);

  return { query, features, catalogLoaded, isLoading, hasSearched, errorMessage, search, clear };
}
