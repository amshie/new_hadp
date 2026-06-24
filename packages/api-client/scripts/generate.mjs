// Generate TypeScript types from the backend OpenAPI document.
// The OpenAPI document is the contract; the generated client is never hand-edited.
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const input = resolve(here, "..", "openapi.json");
const outDir = resolve(here, "..", "src", "generated");
const outFile = resolve(outDir, "schema.ts");

const ast = await openapiTS(new URL(`file://${input}`));
const banner = "// AUTO-GENERATED from packages/api-client/openapi.json. Do not edit by hand.\n";
await mkdir(outDir, { recursive: true });
await writeFile(outFile, banner + astToString(ast), "utf-8");
console.log(`wrote ${outFile}`);
