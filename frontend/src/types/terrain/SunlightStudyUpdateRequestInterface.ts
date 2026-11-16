import type { SunlightStudyRequestInterface } from "./SunlightStudyRequestInterface";

export type SunlightStudyUpdateRequestInterface = Omit<SunlightStudyRequestInterface, "datasetId">;
