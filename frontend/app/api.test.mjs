import assert from "node:assert/strict";
import test from "node:test";
import { listingPayload, listingValues } from "./api.js";

test("editing preserves zeros, multiple tiers and existing listing fields", () => {
  const facility = {
    name: "Example", description: "About", phone: "555", email: "a@example.com", website: "https://example.com",
    address: { street: "1 Main", city: "Olympia", state: "WA", postal_code: "98501" },
    care_levels: [{ id: "memory_care", label: "Memory care" }], amenities: ["Garden"], staff_ratio: "1:5",
    license: { number: "123", state: "WA" }, availability: { beds: 0, waitlist: true, notes: "Call" },
    policies: "Policies", pricing_tiers: [
      { name: "Studio", care_level: "memory_care", monthly_min: 0, monthly_max: 5000, includes: "Meals", id: 1 },
      { name: "Suite", care_level: "", monthly_min: null, monthly_max: null, includes: "", id: 2 },
    ],
  };
  const values = listingValues(facility);
  const payload = listingPayload(values, false);
  assert.equal(payload.beds_available, 0);
  assert.equal(payload.pricing_tiers[0].monthly_min, 0);
  assert.equal(payload.pricing_tiers[1].monthly_min, null);
  assert.equal(payload.pricing_tiers.length, 2);
  assert.deepEqual(payload.care_levels, ["memory_care"]);
  assert.equal(payload.license_number, "123");
  assert.equal(payload.waitlist, true);
  assert.equal(payload.submit, false);
});

test("new listing leaves unknown openings and prices unset", () => {
  const values = listingValues(null);
  values.pricing_tiers.push({ name: "Studio", care_level: "", monthly_min: "", monthly_max: "", includes: "" });
  const payload = listingPayload(values, true);
  assert.equal(payload.beds_available, null);
  assert.equal(payload.pricing_tiers[0].monthly_min, null);
  assert.equal(payload.pricing_tiers[0].monthly_max, null);
  assert.equal(payload.submit, true);
});
