import type { IlluminationProgressInterface } from "../types/terrain/IlluminationProgressInterface";
import { snakeToCamel } from "./caseConversion.ts";
import { ApiStreamError } from "./errorHandling.ts";

type IlluminationEvent<T> =
  { type: "progress"; progress: IlluminationProgressInterface } | { type: "result"; result: T } | { type: "error"; message: string };

export async function readIlluminationStream<T>(
  stream: ReadableStream<Uint8Array>,
  onProgress: (progress: IlluminationProgressInterface) => void
): Promise<T> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let pending = "";

  try {
    while (true) {
      const { value, done } = await reader.read();

      pending += decoder.decode(value, { stream: !done });

      const lines = pending.split("\n");

      pending = lines.pop()!;

      if (done && pending.trim()) {
        lines.push(pending);
      }

      for (const line of lines) {
        if (!line.trim()) {
          continue;
        }

        const event = snakeToCamel(JSON.parse(line)) as IlluminationEvent<T>;

        if (event.type === "progress") {
          onProgress(event.progress);
        } else if (event.type === "result") {
          return event.result;
        } else if (event.type === "error") {
          throw new ApiStreamError(event.message);
        }
      }

      if (done) {
        throw new ApiStreamError("The calculation ended before returning a result. Please try again.");
      }
    }
  } finally {
    try {
      await reader.cancel();
    } finally {
      reader.releaseLock();
    }
  }
}
