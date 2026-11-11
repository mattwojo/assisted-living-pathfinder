export async function api(path, { token, body, ...options } = {}) {
  const headers = { ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  const response = await fetch(`/api${path}`, { ...options, headers, body });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`The server returned an unexpected response (${response.status}).`);
  }
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Please check your entries and try again.";
    throw new Error(detail);
  }
  return data;
}

export function listingValues(facility) {
  if (!facility) return {
    name: "", description: "", phone: "", email: "", website: "", street: "", city: "", state: "",
    postal_code: "", care_levels: [], amenities: [], staff_ratio: "", license_number: "", license_state: "",
    beds_available: "", waitlist: false, availability_notes: "", policies: "", pricing_tiers: [],
  };
  return {
    name: facility.name, description: facility.description, phone: facility.phone, email: facility.email,
    website: facility.website, ...facility.address, care_levels: facility.care_levels.map((item) => item.id),
    amenities: facility.amenities, staff_ratio: facility.staff_ratio, license_number: facility.license.number,
    license_state: facility.license.state, beds_available: facility.availability.beds ?? "",
    waitlist: facility.availability.waitlist, availability_notes: facility.availability.notes,
    policies: facility.policies,
    pricing_tiers: facility.pricing_tiers.map(({ name, care_level, monthly_min, monthly_max, includes }) =>
      ({ name, care_level, monthly_min: monthly_min ?? "", monthly_max: monthly_max ?? "", includes })),
  };
}

export function listingPayload(values, submit) {
  return {
    ...values,
    beds_available: values.beds_available === "" ? null : Number(values.beds_available),
    pricing_tiers: values.pricing_tiers.map((tier) => ({
      ...tier,
      monthly_min: tier.monthly_min === "" ? null : Number(tier.monthly_min),
      monthly_max: tier.monthly_max === "" ? null : Number(tier.monthly_max),
    })),
    submit,
  };
}
