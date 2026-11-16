import type { LocationQuery, Router } from "vue-router";

export function replaceRouteQuery(router: Router, currentQuery: LocationQuery, query: Record<string, string>) {
  const currentEntries = Object.entries(currentQuery).filter((entry): entry is [string, string] => typeof entry[1] === "string");
  const nextEntries = Object.entries(query);

  if (currentEntries.length === nextEntries.length && nextEntries.every(([key, value]) => currentQuery[key] === value)) {
    return;
  }

  void router.replace({ query: nextEntries.length ? query : undefined });
}
