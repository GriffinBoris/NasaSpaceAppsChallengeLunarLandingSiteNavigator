export function snakeFieldAttrToCamel(value: string): string {
  return value.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
}

function convertKeys(value: unknown, convert: (key: string) => string): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => convertKeys(item, convert));
  }

  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [convert(key), convertKeys(item, convert)]));
  }

  return value;
}

export const snakeToCamel = (value: unknown) => convertKeys(value, snakeFieldAttrToCamel);
export const camelToSnake = (value: unknown) => convertKeys(value, (key) => key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`));
