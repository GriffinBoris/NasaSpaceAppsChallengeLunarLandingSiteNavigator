import type { SunlightFrameInterface } from "@/types/terrain/SunlightFrameInterface";
import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";

const HEADER = "site,latitude,longitude,radius_m,timestamp_utc,visible_sun_fraction,visible_earth_fraction,earth_center_visible,joint_visible_share";

export function planResultsCsv(study: SunlightStudyInterface, frames: SunlightFrameInterface[]): string {
  const selections = new Map(study.selections.map((selection, order) => [selection.id, { selection, order }]));
  const sorted = [...frames].sort(
    (first, second) =>
      selections.get(first.selectionId)!.order - selections.get(second.selectionId)!.order ||
      Date.parse(first.timestamp) - Date.parse(second.timestamp)
  );
  const lines = [HEADER];

  for (const frame of sorted) {
    const { selection } = selections.get(frame.selectionId)!;

    lines.push(
      [
        csvText(selection.name),
        selection.latitude,
        selection.longitude,
        selection.radiusMeters ?? "",
        frame.timestamp,
        frame.visibleSunFraction,
        frame.visibleEarthFraction,
        frame.earthCenterVisible,
        frame.jointVisibleShare,
      ].join(",")
    );
  }

  return `${lines.join("\n")}\n`;
}

function csvText(value: string): string {
  const text = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;

  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}
