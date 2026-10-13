// TicketEase frontend matched to the supplied Flask backend (port 5001).
const API_BASE = "http://127.0.0.1:5001";
let shows = [];
let selectedShow = null;
const $ = id => document.getElementById(id);
const safe = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money = n => "₹" + Number(n || 0).toLocaleString("en-IN");
function dateLabel(v) {
  if (!v) return "Date to be announced";
  const d = new Date(String(v).slice(0,10) + "T00:00:00");
  return Number.isNaN(d.getTime()) ? safe(v) : d.toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"});
}
function toast(msg) {
  $("toast").textContent = msg; $("toast").classList.add("show");
  setTimeout(() => $("toast").classList.remove("show"), 3200);
}
async function api(path, options={}) {
  const res = await fetch(API_BASE + path, {
    ...options, headers: {"Content-Type":"application/json", ...(options.headers || {})}
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.message || `Request failed (${res.status})`);
  return data;
}
async function loadShows() {
  const status = $("apiStatus");
  try {
    const data = await api("/api/shows");
    if (!Array.isArray(data)) throw new Error(data.error || "Unexpected response from /api/shows");
    shows = data.map(s => ({
      id: s.Show_ID, name: s.Event_Name, category: s.Event_Type,
      date: s.Show_Date, start: s.Start_Time, end: s.End_Time,
      venue: s.Venue_Name, location: s.Location
    }));
    status.innerHTML = '<span class="status-dot ok"></span> Connected to Flask + MySQL';
    renderEvents();
    if (!shows.length) toast("No upcoming shows were returned by the database.");
  } catch (err) {
    shows = [];
    status.innerHTML = '<span class="status-dot"></span> Backend/database connection failed';
    renderEvents();
    toast("Could not load shows: " + err.message + ". Check MySQL password and start app.py.");
  }
}
function renderEvents() {
  const q = $("searchInput").value.trim().toLowerCase();
  const cat = $("categoryFilter").value.toLowerCase();
  const filtered = shows.filter(s =>
    `${s.name} ${s.category} ${s.venue} ${s.location}`.toLowerCase().includes(q) &&
    (cat === "all" || String(s.category).toLowerCase() === cat)
  );
  $("eventGrid").innerHTML = filtered.map(s => {
    const type = String(s.category || "").toLowerCase();
    const cover = ["music","comedy","theatre"].includes(type) ? "cover-"+type : "";
    return `<article class="event-card">
      <div class="event-cover ${cover}"><span class="event-tag">${safe(s.category)}</span><span class="cover-symbol">✦</span></div>
      <div class="event-body"><div class="event-meta"><span>${safe(dateLabel(s.date))}</span><span>${safe(String(s.start || "").slice(0,5))}</span></div>
      <h3>${safe(s.name)}</h3><div class="event-venue">⌖ ${safe(s.venue)} · ${safe(s.location)}</div>
      <div class="event-foot"><div class="price">Price set at booking</div><button class="btn btn-primary book-btn" data-book="${safe(s.id)}">Book tickets ↗</button></div></div>
    </article>`;
  }).join("");
  $("emptyState").hidden = filtered.length !== 0;
  $("eventGrid").hidden = filtered.length === 0;
  document.querySelectorAll("[data-book]").forEach(btn => btn.addEventListener("click", () => {
    selectedShow = filtered.find(s => String(s.id) === btn.dataset.book);
    openBooking();
  }));
}
function openBooking() {
  if (!selectedShow) return;
  $("bookingTitle").textContent = selectedShow.name;
  $("bookingMeta").textContent = `${dateLabel(selectedShow.date)} · ${String(selectedShow.start || "").slice(0,5)} · ${selectedShow.venue}`;
  $("bookingShowId").value = selectedShow.id;
  $("bookingPrice").value = "250";
  $("bookingSeatId").value = "";
  $("bookingUserId").value = "3";
  $("bookingMessage").textContent = "";
  updateTotal();
  $("bookingDialog").showModal();
}
function updateTotal() {
  const price = Number($("bookingPrice").value || 0);
  const count = Number($("ticketCount").value || 1);
  $("bookingTotal").textContent = money(price * count);
}
async function submitBooking(ev) {
  ev.preventDefault();
  if (!selectedShow) return;
  const payload = {
    user_id: Number($("bookingUserId").value),
    show_id: Number($("bookingShowId").value),
    seat_id: Number($("bookingSeatId").value),
    ticket_type: $("ticketType").value,
    price: Number($("bookingPrice").value)
  };
  if (!payload.user_id || !payload.show_id || !payload.seat_id || !(payload.price >= 0)) {
    $("bookingMessage").textContent = "Enter a valid User ID, Seat ID, and ticket price.";
    return;
  }
  try {
    const result = await api("/api/bookings", {method:"POST", body:JSON.stringify(payload)});
    $("bookingMessage").textContent = `${result.message || "Booking created"} — Booking ID: ${result.booking_id}. Status: ${result.status}.`;
    toast("Booking saved to the database.");
  } catch (err) {
    $("bookingMessage").textContent = "Booking failed: " + err.message;
  }
}
$("searchInput").addEventListener("input", renderEvents);
$("categoryFilter").addEventListener("change", renderEvents);
$("searchBtn").addEventListener("click", () => { renderEvents(); $("events").scrollIntoView({behavior:"smooth"}); });
$("clearFilters").addEventListener("click", () => { $("searchInput").value=""; $("categoryFilter").value="all"; renderEvents(); });
$("loginOpen").addEventListener("click", () => toast("Login is not implemented in the supplied Flask backend yet."));
$("signupOpen").addEventListener("click", () => toast("Registration is not implemented in the supplied Flask backend yet."));
$("bookingForm").addEventListener("submit", submitBooking);
$("ticketCount").addEventListener("change", updateTotal);
$("bookingPrice").addEventListener("input", updateTotal);
loadShows();
