import { computed, ref } from "vue";
import { defineStore } from "pinia";
import type { SunlightSelectionInterface, SunlightSelectionListInterface } from "@/types/terrain/SunlightSelectionInterface";
import type { SunlightSelectionRequestInterface } from "@/types/terrain/SunlightSelectionRequestInterface";
import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
import type { SunlightStudyRequestInterface } from "@/types/terrain/SunlightStudyRequestInterface";
import type { SunlightStudyUpdateRequestInterface } from "@/types/terrain/SunlightStudyUpdateRequestInterface";
import { api } from "@/utils/api";
import { getFirstApiErrorMessage } from "@/utils/errorHandling";
import type { PlanNoticeInterface } from "@/types/terrain/PlanNoticeInterface";
import { isPlanProcessing } from "@/views/home/plan/planTimeline";

const MAXIMUM_NOTICES = 3;

export const useSunlightStore = defineStore("sunlight", () => {
  const selections = ref<SunlightSelectionInterface[]>([]);
  const stepOptions = ref<SunlightSelectionListInterface["stepOptions"]>([]);
  const workerOptions = ref<SunlightSelectionListInterface["workerOptions"]>([]);
  const defaultWorkerCount = ref<number | null>(null);
  const studies = ref<SunlightStudyInterface[]>([]);
  const focusedSelectionId = ref<number | null>(null);
  const pendingStudyIds = ref(new Set<number>());
  const notices = ref<PlanNoticeInterface[]>([]);
  const errorMessage = ref("");
  const isLoading = ref(false);

  const focusedSelection = computed(() => selections.value.find((selection) => selection.id === focusedSelectionId.value) ?? null);
  const hasProcessingStudies = computed(() => studies.value.some(isPlanProcessing));

  let lifecycleVersion = 0;
  let listRequestVersion = 0;
  let selectionListVersion = 0;
  let studyListVersion = 0;
  let noticeNumber = 0;
  let refreshFailureMessage = "";

  function addNotice(notice: Omit<PlanNoticeInterface, "id">) {
    notices.value = [...notices.value, { ...notice, id: ++noticeNumber }].slice(-MAXIMUM_NOTICES);
  }

  function dismissNotice(noticeId: number) {
    notices.value = notices.value.filter((notice) => notice.id !== noticeId);
  }

  async function loadLists() {
    const version = lifecycleVersion;
    const requestVersion = ++listRequestVersion;
    const selectionVersion = selectionListVersion;
    const listVersion = studyListVersion;

    isLoading.value = true;
    errorMessage.value = "";

    try {
      const [selectionList, studyList] = await Promise.all([api.selections.list(), api.studies.list()]);

      if (version !== lifecycleVersion || requestVersion !== listRequestVersion) {
        return;
      }

      if (selectionVersion === selectionListVersion) {
        selections.value = selectionList.selections;
      }

      stepOptions.value = selectionList.stepOptions;
      workerOptions.value = selectionList.workerOptions;
      defaultWorkerCount.value = selectionList.defaultWorkerCount;

      if (listVersion === studyListVersion) {
        studies.value = studyList;
      }
    } catch (error) {
      if (version === lifecycleVersion && requestVersion === listRequestVersion) {
        errorMessage.value = getFirstApiErrorMessage(error, "Unable to load saved sites and plans.");
      }
    } finally {
      if (version === lifecycleVersion && requestVersion === listRequestVersion) {
        isLoading.value = false;
      }
    }
  }

  async function saveSelection(data: SunlightSelectionRequestInterface) {
    const version = lifecycleVersion;

    errorMessage.value = "";

    try {
      const selection = await api.selections.create(data);

      if (version !== lifecycleVersion) {
        return null;
      }

      selectionListVersion++;
      selections.value.push(selection);

      return selection;
    } catch (error) {
      if (version === lifecycleVersion) {
        errorMessage.value = getFirstApiErrorMessage(error, "Unable to save this site.");
      }

      return null;
    }
  }

  async function renameSelection(selectionId: number, name: string) {
    const version = lifecycleVersion;

    errorMessage.value = "";

    try {
      const updated = await api.selections.rename(selectionId, name);

      if (version !== lifecycleVersion) {
        return false;
      }

      selectionListVersion++;
      selections.value = selections.value.map((selection) => (selection.id === selectionId ? updated : selection));

      return true;
    } catch (error) {
      if (version === lifecycleVersion) {
        errorMessage.value = getFirstApiErrorMessage(error, "Unable to rename this site.");
      }

      return false;
    }
  }

  async function removeSelection(selectionId: number) {
    const version = lifecycleVersion;

    errorMessage.value = "";

    try {
      await api.selections.remove(selectionId);

      if (version !== lifecycleVersion) {
        return;
      }

      selectionListVersion++;
      selections.value = selections.value.filter((selection) => selection.id !== selectionId);

      if (focusedSelectionId.value === selectionId) {
        focusedSelectionId.value = null;
      }
    } catch (error) {
      if (version === lifecycleVersion) {
        errorMessage.value = getFirstApiErrorMessage(error, "Unable to delete this site.");
      }
    }
  }

  function focusSelection(selectionId: number | null) {
    focusedSelectionId.value = selectionId;
  }

  async function refreshStudies(signal: AbortSignal) {
    const version = lifecycleVersion;
    const listVersion = studyListVersion;

    try {
      const updatedStudies = await api.studies.list(signal);

      if (signal.aborted || version !== lifecycleVersion || listVersion !== studyListVersion) {
        return;
      }

      studies.value = updatedStudies;

      if (refreshFailureMessage && errorMessage.value === refreshFailureMessage) {
        errorMessage.value = "";
      }

      refreshFailureMessage = "";
    } catch (error) {
      if (!signal.aborted && version === lifecycleVersion && listVersion === studyListVersion) {
        refreshFailureMessage = getFirstApiErrorMessage(error, "Unable to refresh plan progress. Trying again.");
        errorMessage.value = refreshFailureMessage;
      }
    }
  }

  function applyStudySummary(updated: SunlightStudyInterface) {
    studies.value = studies.value.map((study) => (study.id === updated.id ? updated : study));
  }

  async function createStudy(data: SunlightStudyRequestInterface) {
    const version = lifecycleVersion;

    try {
      const study = await api.studies.create(data);

      if (version !== lifecycleVersion) {
        return null;
      }

      studyListVersion++;
      studies.value = [study, ...studies.value];

      return study;
    } catch (error) {
      if (version === lifecycleVersion) {
        await refreshStudies(new AbortController().signal);
      }

      throw error;
    }
  }

  async function updateStudy(studyId: number, data: SunlightStudyUpdateRequestInterface) {
    const version = lifecycleVersion;

    try {
      const study = await api.studies.update(studyId, data);

      if (version !== lifecycleVersion) {
        return;
      }

      studyListVersion++;
      applyStudySummary(study);
    } catch (error) {
      if (version === lifecycleVersion) {
        await refreshStudies(new AbortController().signal);
      }

      throw error;
    }
  }

  async function calculateStudy(studyId: number, workerCount?: number) {
    if (pendingStudyIds.value.has(studyId)) {
      return;
    }

    const version = lifecycleVersion;

    pendingStudyIds.value.add(studyId);
    errorMessage.value = "";

    try {
      const study = await api.studies.calculate(studyId, workerCount);

      if (version !== lifecycleVersion) {
        return;
      }

      studyListVersion++;
      applyStudySummary(study);
    } catch (error) {
      if (version !== lifecycleVersion) {
        return;
      }

      await refreshStudies(new AbortController().signal);

      if (version !== lifecycleVersion) {
        return;
      }

      errorMessage.value = getFirstApiErrorMessage(error, "Unable to queue this plan.");
    } finally {
      if (version === lifecycleVersion) {
        pendingStudyIds.value.delete(studyId);
      }
    }
  }

  async function stopStudy(studyId: number) {
    if (pendingStudyIds.value.has(studyId)) {
      return;
    }

    const version = lifecycleVersion;

    pendingStudyIds.value.add(studyId);
    errorMessage.value = "";

    try {
      const study = await api.studies.stop(studyId);

      if (version !== lifecycleVersion) {
        return;
      }

      studyListVersion++;
      applyStudySummary(study);
    } catch (error) {
      if (version === lifecycleVersion) {
        errorMessage.value = getFirstApiErrorMessage(error, "Unable to stop this plan.");
      }
    } finally {
      if (version === lifecycleVersion) {
        pendingStudyIds.value.delete(studyId);
      }
    }
  }

  async function removeStudy(studyId: number) {
    const version = lifecycleVersion;

    errorMessage.value = "";

    try {
      await api.studies.remove(studyId);

      if (version !== lifecycleVersion) {
        return false;
      }

      studyListVersion++;
      studies.value = studies.value.filter((study) => study.id !== studyId);

      return true;
    } catch (error) {
      if (version === lifecycleVersion) {
        errorMessage.value = getFirstApiErrorMessage(error, "Unable to delete this plan.");
      }

      return false;
    }
  }

  function dispose() {
    lifecycleVersion++;
    pendingStudyIds.value.clear();
    isLoading.value = false;
  }

  return {
    selections,
    stepOptions,
    workerOptions,
    defaultWorkerCount,
    studies,
    focusedSelectionId,
    focusedSelection,
    pendingStudyIds,
    hasProcessingStudies,
    notices,
    addNotice,
    dismissNotice,
    errorMessage,
    isLoading,
    loadLists,
    saveSelection,
    renameSelection,
    removeSelection,
    focusSelection,
    createStudy,
    updateStudy,
    calculateStudy,
    stopStudy,
    refreshStudies,
    removeStudy,
    dispose,
  };
});
