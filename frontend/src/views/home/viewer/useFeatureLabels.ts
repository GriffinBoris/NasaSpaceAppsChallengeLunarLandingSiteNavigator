import { onScopeDispose, shallowRef } from "vue";
import type { LunarFeatureInterface } from "@/types/terrain/LunarFeatureInterface";
import type { FeatureLabelInterface, FeatureLabelQueryInterface, ScreenBoundsInterface } from "@/types/terrain/FeatureLabelInterface";
import { api } from "@/utils/api";
import { getFirstApiErrorMessage } from "@/utils/errorHandling";
import type { FeatureLabelView } from "./featureLabelView";
import { layoutFeatureLabels } from "./featureLabelLayout";

export function useFeatureLabels(
  getView: () => FeatureLabelView | null,
  getReservedBounds: () => ScreenBoundsInterface[],
  measureText: (name: string) => number
) {
  const labels = shallowRef<FeatureLabelInterface[]>([]);
  const errorMessage = shallowRef("");
  let features: LunarFeatureInterface[] = [];
  let frame = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let request: AbortController | null = null;
  let queryKey = "";
  let disposed = false;

  async function load(query: FeatureLabelQueryInterface) {
    const currentRequest = new AbortController();

    request = currentRequest;
    errorMessage.value = "";

    try {
      const result = await api.features.labels(query, currentRequest.signal);

      if (disposed || currentRequest.signal.aborted) {
        return;
      }

      features = result;
      update();
    } catch (error) {
      if (!disposed && !currentRequest.signal.aborted) {
        errorMessage.value = getFirstApiErrorMessage(error, "Feature names could not load. Move the view to retry.");
      }
    } finally {
      if (request === currentRequest) {
        request = null;
      }
    }
  }

  function measure() {
    frame = 0;

    const view = getView();

    if (!view || !view.width || !view.height) {
      labels.value = [];
      return;
    }

    labels.value = layoutFeatureLabels(features, view, getReservedBounds(), measureText);

    const nextKey = JSON.stringify(view.query);

    if (nextKey === queryKey) {
      return;
    }

    queryKey = nextKey;
    request?.abort();
    clearTimeout(timer);
    timer = setTimeout(() => void load(view.query), 200);
  }

  function update() {
    if (!disposed && !frame) {
      frame = requestAnimationFrame(measure);
    }
  }

  onScopeDispose(() => {
    disposed = true;
    clearTimeout(timer);
    cancelAnimationFrame(frame);
    request?.abort();
  });

  return { labels, errorMessage, update };
}
