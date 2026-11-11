"use client";

import { useState } from "react";
import { api, listingPayload, listingValues } from "./api";

const blankTier = () => ({ name: "", care_level: "", monthly_min: "", monthly_max: "", includes: "" });

export default function ListingForm({ facility, meta, token, onSaved, onCancel }) {
  const [values, setValues] = useState(() => listingValues(facility));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key, value) => setValues((old) => ({ ...old, [key]: value }));
  const toggle = (key, value) => set(key, values[key].includes(value) ? values[key].filter((v) => v !== value) : [...values[key], value]);
  const changeTier = (index, key, value) => set("pricing_tiers", values.pricing_tiers.map((tier, i) => i === index ? { ...tier, [key]: value } : tier));

  async function save(event) {
    event.preventDefault();
    const submit = event.nativeEvent.submitter?.value !== "draft";
    setBusy(true); setError("");
    try {
      const result = await api(facility ? `/facilities/${facility.id}` : "/facilities", {
        method: facility ? "PUT" : "POST", token, body: listingPayload(values, submit),
      });
      onSaved(result.facility);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const input = (key, label, props = {}) => <label>{label}<input {...props} value={values[key]} onChange={(e) => set(key, e.target.value)} /></label>;
  return <section className="panel form-panel">
    <div className="section-heading"><div><p className="eyebrow">COMMUNITY PROFILE</p><h2>{facility ? "Edit your listing" : "Add a community"}</h2></div><button className="text-button" type="button" onClick={onCancel}>Cancel</button></div>
    <p>Share what you know. Submitted details are labeled community-provided until reviewed.</p>
    <form onSubmit={save}>
      <fieldset><legend>About the community</legend><div className="form-grid">
        {input("name", "Community name *", { required: true, minLength: 2, maxLength: 120 })}
        {input("phone", "Phone", { type: "tel" })}
        {input("email", "Email", { type: "email" })}
        {input("website", "Website", { type: "url", placeholder: "https://" })}
        <label className="full">Description<textarea value={values.description} onChange={(e) => set("description", e.target.value)} rows="3" /></label>
      </div></fieldset>
      <fieldset><legend>Location</legend><div className="form-grid">
        {input("street", "Street address")}{input("city", "City")}{input("state", "State", { maxLength: 2, placeholder: "WA" })}{input("postal_code", "ZIP code")}
      </div></fieldset>
      <fieldset><legend>Care and amenities</legend>
        <p className="field-label">Care offered</p><div className="check-grid">{meta.care_levels.map((item) => <label className="check" key={item.id}><input type="checkbox" checked={values.care_levels.includes(item.id)} onChange={() => toggle("care_levels", item.id)} />{item.label}</label>)}</div>
        <p className="field-label">Amenities</p><div className="check-grid">{meta.amenities.map((item) => <label className="check" key={item}><input type="checkbox" checked={values.amenities.includes(item)} onChange={() => toggle("amenities", item)} />{item}</label>)}</div>
        <div className="form-grid spaced">{input("staff_ratio", "Staff ratio", { placeholder: "e.g. 1:5" })}{input("license_number", "License number")}{input("license_state", "License state", { maxLength: 2 })}{input("beds_available", "Available openings", { type: "number", min: 0, max: 500, step: 1 })}</div>
        <label className="check spaced"><input type="checkbox" checked={values.waitlist} onChange={(e) => set("waitlist", e.target.checked)} />There is a waitlist</label>
        <label className="spaced">Availability notes<textarea value={values.availability_notes} onChange={(e) => set("availability_notes", e.target.value)} rows="2" /></label>
        <label className="spaced">Policies<textarea value={values.policies} onChange={(e) => set("policies", e.target.value)} rows="3" /></label>
      </fieldset>
      <fieldset><legend>Monthly pricing</legend><p>Include a range when the price varies by room or care needs.</p>
        {values.pricing_tiers.map((tier, index) => <div className="tier" key={index}><div className="section-heading"><h3>Pricing tier {index + 1}</h3><button className="text-button" type="button" onClick={() => set("pricing_tiers", values.pricing_tiers.filter((_, i) => i !== index))}>Remove tier</button></div><div className="form-grid">
          <label>Tier name<input value={tier.name} onChange={(e) => changeTier(index, "name", e.target.value)} placeholder="e.g. Studio" /></label>
          <label>Care level<select value={tier.care_level} onChange={(e) => changeTier(index, "care_level", e.target.value)}><option value="">Not specified</option>{meta.care_levels.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
          <label>Minimum per month ($)<input type="number" min="0" step="0.01" value={tier.monthly_min} onChange={(e) => changeTier(index, "monthly_min", e.target.value)} /></label>
          <label>Maximum per month ($)<input type="number" min="0" step="0.01" value={tier.monthly_max} onChange={(e) => changeTier(index, "monthly_max", e.target.value)} /></label>
          <label className="full">What is included?<input value={tier.includes} onChange={(e) => changeTier(index, "includes", e.target.value)} /></label>
        </div></div>)}
        <button type="button" className="button secondary" onClick={() => set("pricing_tiers", [...values.pricing_tiers, blankTier()])}>+ Add pricing tier</button>
      </fieldset>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="actions"><button className="button" type="submit" value="submit" disabled={busy}>{busy ? "Saving..." : "Submit listing"}</button><button className="button secondary" type="submit" value="draft" disabled={busy}>Save as draft</button></div>
      <p className="hint">Submitting makes this listing visible in search, even if it is waiting for review. A draft is only visible to its owner and reviewers.</p>
    </form>
  </section>;
}
