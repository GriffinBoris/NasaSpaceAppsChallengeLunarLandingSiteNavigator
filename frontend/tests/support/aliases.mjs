import { URL } from "node:url";

const sourceRoot = new URL("../../src/", import.meta.url);

export function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith("@/")) {
    return nextResolve(new URL(`${specifier.slice(2)}.ts`, sourceRoot).href, context);
  }

  if (context.parentURL?.startsWith(sourceRoot.href) && specifier.startsWith(".") && !specifier.endsWith(".ts")) {
    return nextResolve(new URL(`${specifier}.ts`, context.parentURL).href, context);
  }

  return nextResolve(specifier, context);
}
