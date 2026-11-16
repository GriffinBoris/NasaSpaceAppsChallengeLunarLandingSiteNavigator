export interface PlanNoticeInterface {
  id: number;
  studyId: number | null;
  message: string;
  tone: "success" | "error";
}
