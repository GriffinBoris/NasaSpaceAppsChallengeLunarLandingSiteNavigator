import type { SunlightFrameInterface } from "@/types/terrain/SunlightFrameInterface";

export function mergeFrames(
  currentFrames: SunlightFrameInterface[],
  changedFrames: SunlightFrameInterface[],
  resetHistory: boolean
): SunlightFrameInterface[] {
  if (resetHistory) {
    return changedFrames;
  }

  if (!changedFrames.length) {
    return currentFrames;
  }

  const framesById = new Map<number, SunlightFrameInterface>();

  for (const frame of currentFrames) {
    framesById.set(frame.id, frame);
  }

  for (const changedFrame of changedFrames) {
    const previousFrame = framesById.get(changedFrame.id);

    if (previousFrame && changedFrame.resultRevision < previousFrame.resultRevision) {
      continue;
    }

    framesById.set(changedFrame.id, changedFrame);
  }

  const mergedFrames = [...framesById.values()];

  mergedFrames.sort((firstFrame, secondFrame) => {
    const timestampOrder = firstFrame.timestamp.localeCompare(secondFrame.timestamp);

    if (timestampOrder !== 0) {
      return timestampOrder;
    }

    return firstFrame.selectionId - secondFrame.selectionId;
  });

  return mergedFrames;
}
