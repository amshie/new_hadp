// Contract test for the generated API client: asserts the OpenAPI document the client is
// generated from contains the endpoints the frontend depends on. Runs with `node --test`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
const openapi = JSON.parse(readFileSync(resolve(here, "..", "openapi.json"), "utf-8"));

test("openapi document exposes the endpoints the web app uses", () => {
  const expected = [
    "/api/v1/auth/dev-login",
    "/api/v1/auth/me",
    "/api/v1/tenancy/my-tenants",
    "/api/v1/tenancy/select-tenant",
    "/api/v1/patients",
    "/api/v1/patients/{patient_id}/observations",
    "/api/v1/patients/{patient_id}/reports",
    "/api/v1/reports/{report_id}/approve",
    "/api/v1/reports/{report_id}/release",
    "/api/v1/patient-view",
  ];
  for (const path of expected) {
    assert.ok(openapi.paths[path], `missing OpenAPI path: ${path}`);
  }
});

test("generated schema module exists", () => {
  const schema = readFileSync(resolve(here, "..", "src", "generated", "schema.ts"), "utf-8");
  assert.match(schema, /export interface paths/);
});
