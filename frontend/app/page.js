"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import ListingForm from "./ListingForm";

function Photo({ photo, token }) {
  const [url, setUrl] = useState("");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    let objectUrl;
    setUrl(""); setFailed(false);
    fetch(photo.url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((response) => {
        if (!response.ok) throw new Error("Photo unavailable");
        return response.blob();
      })
      .then((blob) => {
        if (active) { objectUrl = URL.createObjectURL(blob); setUrl(objectUrl); }
      })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [photo.url, token]);
  return url ? <img src={url} alt={photo.caption || "Community photo"} /> : <div className="photo-placeholder">{failed ? "Photo unavailable" : "Loading photo..."}</div>;
}

function money(value) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(value);
}

function price(facility) {
  const amounts = facility.pricing_tiers.map((tier) => tier.monthly_min).filter((value) => value != null);
  return amounts.length ? `From ${money(Math.min(...amounts))} / month` : "Price not recorded";
}

function Badge({ facility }) {
  return <span className={`badge ${facility.validation.status}`}>{facility.validation.label}</span>;
}

function Card({ result, onOpen, selected, onCompare }) {
  const { facility, matched, missed } = result;
  return <article className="result-card">
    <div className="card-top"><span className="location">{[facility.address.city, facility.address.state].filter(Boolean).join(", ") || "Location not recorded"}</span><Badge facility={facility} /></div>
    <h3><button className="card-link" onClick={() => onOpen(facility.id)}>{facility.name}</button></h3>
    <p className="card-description">{facility.description || "No description provided."}</p>
    <div className="card-tags">{facility.care_levels.map((care) => <span key={care.id}>{care.label}</span>)}</div>
    <div className="card-meta"><strong>{price(facility)}</strong><span>{facility.availability.beds == null ? "Availability not recorded" : `${facility.availability.beds} openings reported`}</span></div>
    {(matched.length > 0 || missed.length > 0) && <div className="match-reasons">{matched.map((reason) => <p key={reason}>✓ {reason}</p>)}{missed.map((reason) => <p key={reason}>• {reason}</p>)}</div>}
    <div className="card-actions"><button className="text-button" onClick={() => onOpen(facility.id)}>Explore community <span aria-hidden="true">→</span></button><label className="check"><input type="checkbox" checked={selected} onChange={() => onCompare(facility)} /> Compare</label></div>
  </article>;
}

function Auth({ onAuth }) {
  const [register, setRegister] = useState(false);
  const [values, setValues] = useState({ name: "", email: "", password: "", role: "family" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError("");
    try { onAuth(await api(`/auth/${register ? "register" : "login"}`, { method: "POST", body: values })); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <section className="panel narrow"><p className="eyebrow">WELCOME</p><h2>{register ? "Create an account" : "Sign in"}</h2><p>Represent a community? Sign in to manage your listings.</p>
    <form onSubmit={submit} className="stack">
      {register && <label>Name<input required minLength="2" maxLength="80" autoComplete="name" value={values.name} onChange={(e) => setValues({ ...values, name: e.target.value })} /></label>}
      <label>Email<input required type="email" autoComplete="email" value={values.email} onChange={(e) => setValues({ ...values, email: e.target.value })} /></label>
      <label>Password<input required minLength={register ? 8 : undefined} type="password" autoComplete={register ? "new-password" : "current-password"} value={values.password} onChange={(e) => setValues({ ...values, password: e.target.value })} /></label>
      {register && <label>I am a<select value={values.role} onChange={(e) => setValues({ ...values, role: e.target.value })}><option value="family">Family member or older adult</option><option value="representative">Community representative</option></select></label>}
      {error && <p className="error" role="alert">{error}</p>}
      <button className="button" disabled={busy}>{busy ? "Please wait..." : register ? "Create account" : "Sign in"}</button>
    </form>
    <p><button className="text-button" onClick={() => { setRegister(!register); setError(""); }}>{register ? "Already have an account? Sign in" : "New here? Create an account"}</button></p>
  </section>;
}

function PhotoManager({ facility, token, refresh }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function perform(action) {
    setError(""); setBusy(true);
    try { await action(); await refresh(); } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function upload(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await perform(async () => { await api(`/facilities/${facility.id}/photos`, { method: "POST", token, body: data }); form.reset(); });
  }
  function move(index, direction) {
    const ids = facility.photos.map((photo) => photo.id);
    const next = index + direction;
    [ids[index], ids[next]] = [ids[next], ids[index]];
    perform(() => api(`/facilities/${facility.id}/photos/reorder`, { method: "POST", token, body: { photo_ids: ids } }));
  }
  return <div className="detail-block"><h3>Manage photos</h3><p>JPEG, PNG, or WebP, up to 5 MB.</p>
    <div className="photo-list">{facility.photos.map((photo, index) => <div className="photo-edit" key={photo.id}><Photo photo={photo} token={token} />
      <form onSubmit={(event) => { event.preventDefault(); const caption = new FormData(event.currentTarget).get("caption"); perform(() => api(`/photos/${photo.id}`, { method: "PATCH", token, body: { caption } })); }}>
        <label>Caption<input name="caption" defaultValue={photo.caption} maxLength="180" /></label><div className="actions"><button className="text-button" disabled={busy}>Save caption</button><button type="button" className="text-button" disabled={busy || index === 0} onClick={() => move(index, -1)}>Move earlier</button><button type="button" className="text-button" disabled={busy || index === facility.photos.length - 1} onClick={() => move(index, 1)}>Move later</button><button type="button" className="text-button danger" disabled={busy} onClick={() => { if (confirm("Remove this photo?")) perform(() => api(`/photos/${photo.id}`, { method: "DELETE", token })); }}>Remove</button></div>
      </form></div>)}</div>
    <form onSubmit={upload} className="form-grid spaced"><label>Choose a photo<input name="file" type="file" accept="image/jpeg,image/png,image/webp" required /></label><label>Caption<input name="caption" maxLength="180" /></label><div><button className="button secondary" disabled={busy}>Upload photo</button></div></form>
    {error && <p className="error" role="alert">{error}</p>}
  </div>;
}

function Detail({ facility, token, user, onBack, onEdit, refresh }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const canEdit = user && (user.role === "admin" || (user.role === "representative" && user.id === facility.owner_user_id));
  async function ask(event) {
    event.preventDefault(); setError(""); setAnswer(null); setBusy(true);
    try { setAnswer(await api(`/facilities/${facility.id}/questions`, { method: "POST", token, body: { question } })); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function review(fact, action) {
    setError("");
    try { await api(`/facts/${fact.id}/${action}`, { method: "POST", token }); await refresh(); }
    catch (err) { setError(err.message); }
  }
  return <div><button className="back-link" onClick={onBack}>← Back</button>
    <section className="detail-header"><div><p className="eyebrow">{[facility.address.city, facility.address.state].filter(Boolean).join(", ") || "LOCATION NOT RECORDED"}</p><h1>{facility.name}</h1><p>{facility.description || "No description provided."}</p><Badge facility={facility} /></div>{canEdit && <button className="button secondary" onClick={onEdit}>Edit listing</button>}</section>
    <div className="detail-layout"><div>
      {facility.photos.length > 0 && <div className="gallery">{facility.photos.map((photo) => <figure key={photo.id}><Photo photo={photo} token={token} /><figcaption>{photo.caption}</figcaption></figure>)}</div>}
      <section className="detail-block"><h2>At a glance</h2><div className="facts-grid"><div><span>Care offered</span><strong>{facility.care_levels.map((x) => x.label).join(", ") || "Not recorded"}</strong></div><div><span>Starting price</span><strong>{price(facility)}</strong></div><div><span>Availability</span><strong>{facility.availability.beds == null ? "Not recorded" : `${facility.availability.beds} openings reported`}{facility.availability.waitlist ? "; waitlist" : ""}</strong></div><div><span>Staff ratio</span><strong>{facility.staff_ratio || "Not recorded"}</strong></div></div><p>Prices and openings can change. Confirm details directly with the community.</p></section>
      <section className="detail-block"><h2>Ask about this community</h2><p>Explore recorded information about care, costs, availability, and more.</p><form onSubmit={ask}><label htmlFor="question">Your question</label><textarea id="question" required minLength="3" maxLength="1000" rows="3" placeholder="What is included in the monthly price?" value={question} onChange={(e) => setQuestion(e.target.value)} /><button className="button spaced" disabled={busy}>{busy ? "Finding an answer..." : "Ask a question"}</button></form>
        {error && <p className="error" role="alert">{error}</p>}
        {answer && <div className="answer" aria-live="polite"><h3>Answer</h3><p className="preserve">{answer.answer}</p>{answer.uncertainty.map((item) => <p key={item}><strong>Please note:</strong> {item}</p>)}{answer.citations.length > 0 && <><h4>Sources used</h4><ul>{answer.citations.map((item, index) => <li key={index}>{item.label}: {item.value} — {item.source_label}, {item.verification_status.replaceAll("_", " ")}; last checked {item.last_checked || "unknown"}</li>)}</ul></>}</div>}
      </section>
      <section className="detail-block"><h2>Information & sources</h2><p>These are the recorded claims and their sources. Verification of one fact does not verify the entire listing.</p>
        {facility.validation.flags.map((flag, index) => <p className="notice" key={index}>{flag.message}</p>)}
        <div className="source-list">{facility.facts.map((fact) => <div className={`source ${!fact.active ? "inactive" : ""}`} key={fact.id}><div><strong>{fact.label}</strong><p>{fact.value}</p><small>{fact.source_label} · {fact.verification_label} · Last checked {fact.last_checked || "unknown"}{!fact.active && " · Set aside"}</small></div>{user?.role === "admin" && fact.active && <div className="actions"><button className="text-button" onClick={() => review(fact, "verify")}>Mark verified</button><button className="text-button danger" onClick={() => review(fact, "set-aside")}>Set aside</button></div>}</div>)}</div>
      </section>
      {canEdit && <PhotoManager facility={facility} token={token} refresh={refresh} />}
    </div><aside className="panel contact"><h2>Community details</h2><p>{[facility.address.street, facility.address.city, facility.address.state, facility.address.postal_code].filter(Boolean).join(", ") || "Address not recorded"}</p><p><strong>Phone</strong><br />{facility.phone || "Not recorded"}</p><p><strong>Email</strong><br />{facility.email || "Not recorded"}</p><p><strong>License</strong><br />{[facility.license.state, facility.license.number].filter(Boolean).join(" ") || "Not recorded"}</p><p><strong>Amenities</strong><br />{facility.amenities.join(", ") || "Not recorded"}</p></aside></div>
  </div>;
}

export default function Home() {
  const [meta, setMeta] = useState(null);
  const [page, setPage] = useState("search");
  const [user, setUser] = useState(null);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({ city: "", state: "", max_budget: "", care_levels: [], amenities: [], available_only: false });
  const [results, setResults] = useState(null);
  const [busy, setBusy] = useState(false);
  const [facility, setFacility] = useState(null);
  const [owned, setOwned] = useState([]);
  const [compare, setCompare] = useState([]);
  const [origin, setOrigin] = useState("search");

  const search = useCallback(async (q, f) => {
    setBusy(true); setError("");
    try { setResults(await api("/search", { method: "POST", body: { ...f, query: q, max_budget: f.max_budget === "" ? null : Number(f.max_budget) } })); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }, []);

  useEffect(() => {
    api("/meta").then(setMeta).catch((err) => setError(`Could not load the app: ${err.message}`));
    const saved = sessionStorage.getItem("pathfinder_token");
    if (saved) api("/auth/me", { token: saved }).then((data) => { setUser(data.user); setToken(saved); }).catch(() => { sessionStorage.removeItem("pathfinder_token"); setNotice("Your session could not be restored. Please sign in again."); });
    search("", { city: "", state: "", max_budget: "", care_levels: [], amenities: [], available_only: false });
  }, [search]);

  async function openFacility(id, from = page) {
    setError("");
    try { const data = await api(`/facilities/${id}`, { token }); setFacility(data.facility); setOrigin(from); setPage("detail"); window.scrollTo(0, 0); }
    catch (err) { setError(err.message); }
  }
  async function refresh() {
    const data = await api(`/facilities/${facility.id}`, { token });
    setFacility(data.facility);
    setCompare((old) => old.map((item) => item.id === data.facility.id ? data.facility : item));
  }
  async function openOwned(review = false) {
    setError(""); setBusy(true);
    try { const data = await api(review ? "/review/facilities" : "/my/facilities", { token }); setOwned(data.facilities); setPage(review ? "review" : "manage"); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  function auth(data) { sessionStorage.setItem("pathfinder_token", data.token); setToken(data.token); setUser(data.user); setCompare([]); setPage("search"); setNotice(`Signed in as ${data.user.name}.`); }
  async function logout() {
    setError("");
    try { await api("/auth/logout", { method: "POST", token }); sessionStorage.removeItem("pathfinder_token"); setToken(""); setUser(null); setFacility(null); setOwned([]); setCompare([]); setPage("search"); setNotice("Signed out."); }
    catch (err) { setError(err.message); }
  }
  function toggleCompare(item) { setCompare((old) => old.some((f) => f.id === item.id) ? old.filter((f) => f.id !== item.id) : [...old, item]); }
  const setFilter = (key, value) => setFilters((old) => ({ ...old, [key]: value }));

  return <><a className="skip-link" href="#main">Skip to content</a><header className="site-header"><div className="header-inner"><button className="brand" onClick={() => setPage("search")}><span className="brand-mark" aria-hidden="true">✳</span><span>Assisted Living <b>Pathfinder</b></span></button><nav aria-label="Main navigation"><button className={page === "search" ? "nav-active" : ""} onClick={() => setPage("search")}>Find a community</button>{user && ["representative", "admin"].includes(user.role) && <button onClick={() => openOwned()}>My listings</button>}{user?.role === "admin" && <button onClick={() => openOwned(true)}>Review</button>}{user ? <button onClick={logout}>Sign out</button> : <button onClick={() => { setPage("auth"); setError(""); }}>Sign in</button>}</nav></div></header>
    <main id="main" tabIndex="-1">
      {notice && <div className="global-notice" role="status">{notice}<button className="text-button" onClick={() => setNotice("")}>Dismiss</button></div>}
      {error && <div className="error global-error" role="alert">{error}</div>}
      {page === "search" && <><section className="hero"><div className="hero-inner"><p className="eyebrow light">A MORE INFORMED NEXT STEP</p><h1>Find a place to<br /><em>feel at home.</em></h1><p>Explore assisted living communities with clearer information, helpful context, and room to ask questions.</p><form className="hero-search" onSubmit={(e) => { e.preventDefault(); search(query, filters); }}><label className="sr-only" htmlFor="query">Describe what you are looking for</label><input id="query" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Try “memory care near Bothell under $6,000”" /><button className="button">Search communities <span aria-hidden="true">→</span></button></form><p className="hero-hint">Search in your own words, or use the filters below.</p></div><div className="hero-art" aria-hidden="true"><div className="art-sun"></div><div className="art-house"><div className="art-roof"></div><div className="art-door"></div><div className="art-window"></div></div><div className="art-hill"></div><span>Thoughtful choices<br />start here.</span></div></section>
        <div className="content"><div className="sample-note"><span aria-hidden="true">ⓘ</span><div><strong>A place to explore, not a directory yet.</strong> {meta?.sample_data_note || "Sample community listings are fictional."} Confirm all details independently.</div></div>
          <div className="search-layout"><aside className="filters panel"><div className="section-heading"><h2>Refine your search</h2></div><form onSubmit={(e) => { e.preventDefault(); search(query, filters); }} className="stack"><label>City<input value={filters.city} onChange={(e) => setFilter("city", e.target.value)} placeholder="Any city" /></label><label>State<input value={filters.state} onChange={(e) => setFilter("state", e.target.value)} maxLength="2" placeholder="e.g. WA" /></label><label>Maximum monthly budget ($)<input type="number" min="0" step="1" value={filters.max_budget} onChange={(e) => setFilter("max_budget", e.target.value)} placeholder="No maximum" /></label><label>Care type<select value={filters.care_levels[0] || ""} onChange={(e) => setFilter("care_levels", e.target.value ? [e.target.value] : [])}><option value="">All care types</option>{meta?.care_levels.map((care) => <option key={care.id} value={care.id}>{care.label}</option>)}</select></label><label>Amenity<select value={filters.amenities[0] || ""} onChange={(e) => setFilter("amenities", e.target.value ? [e.target.value] : [])}><option value="">Any amenity</option>{meta?.amenities.map((item) => <option key={item}>{item}</option>)}</select></label><label className="check"><input type="checkbox" checked={filters.available_only} onChange={(e) => setFilter("available_only", e.target.checked)} />Reported openings only</label><button className="button secondary">Apply filters</button><button type="button" className="text-button" onClick={() => { const clear = { city: "", state: "", max_budget: "", care_levels: [], amenities: [], available_only: false }; setFilters(clear); setQuery(""); search("", clear); }}>Clear search</button></form></aside>
            <section aria-label="Search results"><div className="results-heading"><div><p className="eyebrow">EXPLORE YOUR OPTIONS</p><h2>Communities for you</h2><p>{busy ? "Searching..." : results ? `${results.matches.length} matching ${results.matches.length === 1 ? "community" : "communities"}` : "Search to see communities."}</p></div>{compare.length > 0 && <button className="button secondary" onClick={() => setPage("compare")}>Compare ({compare.length})</button>}</div>
              {results && !busy && <><p className="hint">Recognized criteria: {[
                ...results.interpreted.care_levels.map((id) => meta?.care_levels.find((item) => item.id === id)?.label || id),
                results.interpreted.city && `${results.interpreted.city_mode === "near" ? "Near" : "In"} ${results.interpreted.city}`,
                results.interpreted.state && `State: ${results.interpreted.state}`,
                results.interpreted.max_budget != null && `Budget: up to ${money(results.interpreted.max_budget)}/month`,
                ...results.interpreted.amenities,
                results.interpreted.available_only && "Reported openings",
                results.interpreted.wants_high_staff && "High staff ratio",
              ].filter(Boolean).join(" · ") || "None"}. Free-text location recognition and nearby matching cover a limited list of cities; use the city filter for other locations.</p><div className="results-grid">{results.matches.map((result) => <Card key={result.facility.id} result={result} onOpen={openFacility} selected={compare.some((f) => f.id === result.facility.id)} onCompare={toggleCompare} />)}</div>{results.matches.length === 0 && <div className="empty"><h3>No exact matches</h3><p>Try a different search or remove a filter. Close matches may still be useful.</p></div>}{results.close.length > 0 && <><h2 className="close-heading">Other communities to consider</h2><p>These do not meet every search criterion. Review the differences below.</p><div className="results-grid">{results.close.map((result) => <Card key={result.facility.id} result={result} onOpen={openFacility} selected={compare.some((f) => f.id === result.facility.id)} onCompare={toggleCompare} />)}</div></>}</>}
            </section></div></div></>}
      {page === "auth" && <div className="content"><Auth onAuth={auth} /></div>}
      {page === "detail" && facility && <div className="content"><Detail key={facility.id} facility={facility} token={token} user={user} onBack={() => { if (origin === "manage" || origin === "review") openOwned(origin === "review"); else setPage(origin); }} onEdit={() => setPage("edit")} refresh={refresh} /></div>}
      {(page === "manage" || page === "review") && <div className="content"><div className="section-heading"><div><p className="eyebrow">YOUR WORKSPACE</p><h1>{page === "review" ? "Listings for review" : "My listings"}</h1><p>{page === "review" ? "Review recorded claims and their sources." : "Create and maintain your community profiles."}</p></div>{page === "manage" && <button className="button" onClick={() => { setFacility(null); setPage("edit"); }}>+ Add a community</button>}</div>{owned.length ? <div className="results-grid">{owned.map((item) => <Card key={item.id} result={{ facility: item, matched: [], missed: [] }} onOpen={openFacility} selected={compare.some((f) => f.id === item.id)} onCompare={toggleCompare} />)}</div> : <div className="empty">No listings here yet.</div>}</div>}
      {page === "edit" && meta && <div className="content"><ListingForm key={facility?.id || "new"} facility={facility} meta={meta} token={token} onCancel={() => facility ? setPage("detail") : openOwned()} onSaved={(saved) => { setFacility(saved); setCompare((old) => old.map((item) => item.id === saved.id ? saved : item)); setOrigin("manage"); setPage("detail"); setNotice(saved.published ? "Listing submitted. Review its status and sources below." : "Draft saved."); search(query, filters); }} /></div>}
      {page === "compare" && <div className="content"><button className="back-link" onClick={() => setPage("search")}>← Back to search</button><p className="eyebrow">SIDE BY SIDE</p><h1>Compare communities</h1><p>Starting prices and openings are reported figures, not quotes or guarantees.</p>{compare.length === 0 ? <p>No communities selected.</p> : <div className="comparison">{compare.map((item) => <article className="panel" key={item.id}><h2>{item.name}</h2><Badge facility={item} /><p><strong>Location:</strong> {[item.address.city, item.address.state].filter(Boolean).join(", ") || "Not recorded"}</p><p><strong>Care:</strong> {item.care_levels.map((c) => c.label).join(", ") || "Not recorded"}</p><p><strong>Pricing:</strong> {price(item)}</p><p><strong>Availability:</strong> {item.availability.beds == null ? "Not recorded" : `${item.availability.beds} openings reported`}{item.availability.waitlist ? "; waitlist" : ""}</p><p><strong>Amenities:</strong> {item.amenities.join(", ") || "Not recorded"}</p><button className="text-button" onClick={() => openFacility(item.id, "compare")}>View sources and details →</button><br /><button className="text-button danger" onClick={() => toggleCompare(item)}>Remove from comparison</button></article>)}</div>}</div>}
    </main><footer><div><strong>Assisted Living Pathfinder</strong><p>Information for a more confident conversation.</p></div><p>General information only. Not medical, legal, or financial advice.</p></footer></>;
}
