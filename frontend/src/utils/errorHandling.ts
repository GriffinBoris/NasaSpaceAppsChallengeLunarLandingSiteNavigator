import { isAxiosError } from "axios";
import type { ErrorResponseInterface } from "@/types/api/ErrorResponseInterface";

export class ApiStreamError extends Error {}

export function getApiErrorStatus(error: unknown): number | null {
  if (!isAxiosError(error)) {
    return null;
  }

  return error.response?.status ?? null;
}

export function getFirstApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiStreamError) {
    return error.message;
  }
  if (!isAxiosError<ErrorResponseInterface>(error)) {
    return fallback;
  }

  return error.response?.data?.errors?.[0]?.detail ?? fallback;
}

export function getFirstApiErrorCode(error: unknown): string | null {
  if (!isAxiosError<ErrorResponseInterface>(error)) {
    return null;
  }

  return error.response?.data?.errors?.[0]?.code ?? null;
}
