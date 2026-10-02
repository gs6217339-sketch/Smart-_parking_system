"""
frontend/app.py  —  Streamlit UI
ONLY handles display and user interaction.
ALL data fetched from FastAPI backend via api_client.py.
No DB, no SQL, no business logic here.

Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from api_client import (
    api_register, api_login, api_stats, api_locations,
    api_slots, api_nearby, api_park, api_checkout,
    api_search, api_compare_prices, api_vehicle_types,
    api_bookings, api_analytics, api_health
)

# ══════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Smart Parking System",
    page_icon="🅿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════
defaults = {
    "logged_in":  False,
    "username":   "",
    "token":      "",
    "dark_mode":  True,
    "active_loc": None,
    "last_qr":    None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════
#  THEME
# ══════════════════════════════════════════════════════════════
def get_theme():
    if st.session_state.dark_mode:
        return {
            "bg": "#0a0f1e", "bg2": "#111827", "bg3": "#1e293b",
            "card": "#111827", "border": "#1e3a5f", "border2": "#334155",
            "text": "#f1f5f9", "muted": "#94a3b8", "sub": "#64748b",
            "primary": "#3b82f6", "green": "#22c55e",
            "red": "#ef4444", "yellow": "#f59e0b",
            "slot_free": "rgba(34,197,94,.12)",
            "slot_occ": "rgba(239,68,68,.14)",
            "auth_bg": "linear-gradient(135deg,#1e3a5f,#0f172a)",
            "bill_bg": "linear-gradient(135deg,#0c1f3f,#111827)",
            "bill_border": "#1e40af",
            "metric_bg": "linear-gradient(135deg,#111827,#1e293b)",
            "mode_icon": "☀️", "mode_label": "Light Mode",
        }
    return {
        "bg": "#f0f4f8", "bg2": "#ffffff", "bg3": "#e2e8f0",
        "card": "#ffffff", "border": "#cbd5e1", "border2": "#94a3b8",
        "text": "#0f172a", "muted": "#475569", "sub": "#64748b",
        "primary": "#2563eb", "green": "#16a34a",
        "red": "#dc2626", "yellow": "#d97706",
        "slot_free": "rgba(22,163,74,.10)",
        "slot_occ": "rgba(220,38,38,.10)",
        "auth_bg": "linear-gradient(135deg,#dbeafe,#eff6ff)",
        "bill_bg": "linear-gradient(135deg,#dbeafe,#eff6ff)",
        "bill_border": "#93c5fd",
        "metric_bg": "linear-gradient(135deg,#ffffff,#f1f5f9)",
        "mode_icon": "🌙", "mode_label": "Dark Mode",
    }


def inject_css():
    t = get_theme()
    st.markdown(f"""
    <style>
    html,body,[data-testid="stAppViewContainer"]{{
        background:{t['bg']} !important; color:{t['text']} !important;
    }}
    [data-testid="stSidebar"]{{
        background:#0d1526 !important;
        border-right:1px solid {t['border']};
    }}
    [data-testid="stSidebar"] *{{ color:#f1f5f9 !important; }}
    [data-testid="metric-container"]{{
        background:{t['metric_bg']};
        border:1px solid {t['border']};
        border-radius:14px; padding:16px 20px !important;
    }}
    [data-testid="stMetricValue"]{{font-size:2rem !important; font-weight:800 !important; color:{t['text']} !important;}}
    [data-testid="stMetricLabel"]{{font-size:.82rem !important; color:{t['muted']} !important;}}
    .page-title{{
        background:{t['auth_bg']}; border-left:4px solid {t['primary']};
        border-radius:10px; padding:14px 22px; margin-bottom:24px;
    }}
    .page-title h2{{margin:0;font-size:1.5rem;color:{t['text']};font-weight:700;}}
    .page-title p {{margin:0;font-size:.85rem;color:{t['muted']};}}
    .sec{{
        font-size:.78rem; font-weight:700; text-transform:uppercase;
        letter-spacing:.1em; color:{t['primary']};
        margin:22px 0 10px; display:flex; align-items:center; gap:8px;
    }}
    .sec::after{{content:'';flex:1;height:1px;background:{t['border']};}}
    .slot-free{{
        background:{t['slot_free']}; border:1.5px solid {t['green']};
        border-radius:10px; padding:12px 8px; text-align:center;
        font-size:12px; min-height:78px;
    }}
    .slot-occ{{
        background:{t['slot_occ']}; border:1.5px solid {t['red']};
        border-radius:10px; padding:12px 8px; text-align:center;
        font-size:12px; min-height:78px;
    }}
    .slot-num{{font-size:10px;color:{t['sub']};margin-bottom:4px;}}
    .slot-lbl{{font-weight:800;font-size:13px;margin:3px 0;}}
    .slot-sub{{font-size:11px;color:{t['muted']};}}
    .bill-card{{
        background:{t['bill_bg']}; border:1px solid {t['bill_border']};
        border-radius:16px; padding:24px 30px; max-width:380px;
    }}
    .bill-title{{color:{t['primary']};font-size:1.1rem;font-weight:800;margin-bottom:16px;}}
    .bill-row{{display:flex;justify-content:space-between;
               padding:8px 0;border-bottom:1px solid {t['border']};
               font-size:.92rem;color:{t['muted']};}}
    .bill-row strong{{color:{t['text']};}}
    .bill-total{{display:flex;justify-content:space-between;padding:14px 0 0;font-size:1.1rem;font-weight:700;}}
    .bill-total .amt{{color:{t['green']};font-size:1.4rem;}}
    .auth-banner{{
        background:{t['auth_bg']}; border:1px solid {t['bill_border']};
        border-radius:16px; padding:28px 32px;
        text-align:center; margin-bottom:20px;
    }}
    .auth-title{{font-size:1.6rem;font-weight:800;color:{t['text']};margin-top:8px;}}
    .auth-sub{{font-size:.9rem;color:{t['sub']};}}
    .occ-bar-wrap{{background:{t['bg3']};border-radius:6px;height:8px;margin:8px 0 14px;overflow:hidden;}}
    .occ-bar{{height:100%;border-radius:6px;background:linear-gradient(90deg,{t['green']},#16a34a);}}
    .occ-bar.warn{{background:linear-gradient(90deg,{t['yellow']},#d97706);}}
    .occ-bar.danger{{background:linear-gradient(90deg,{t['red']},#dc2626);}}
    .price-table{{width:100%;border-collapse:collapse;font-size:.88rem;}}
    .price-table th{{background:{t['bg3']};color:{t['muted']};padding:10px 14px;
                     text-align:left;font-size:.75rem;text-transform:uppercase;
                     border-bottom:1px solid {t['border']};}}
    .price-table td{{padding:12px 14px;border-bottom:1px solid {t['bg']};color:{t['text']};}}
    .price-table tr:hover td{{background:rgba(59,130,246,.06);}}
    .price-table tr.cheapest td{{background:rgba(34,197,94,.08);}}
    .price-table tr.cheapest td:first-child{{border-left:3px solid {t['green']};}}
    .rate-chip{{background:{t['bg3']};border:1px solid {t['border2']};
                border-radius:20px;padding:3px 10px;font-size:.8rem;
                font-weight:700;color:{t['yellow']};display:inline-block;}}
    .avail-chip{{font-size:.78rem;font-weight:600;padding:2px 9px;border-radius:20px;}}
    .avail-yes{{background:rgba(34,197,94,.15);color:{t['green']};}}
    .avail-no{{background:rgba(239,68,68,.15);color:{t['red']};}}
    .best-badge{{background:linear-gradient(90deg,#065f46,#047857);color:#6ee7b7;
                 font-size:.72rem;font-weight:700;padding:2px 9px;
                 border-radius:20px;display:inline-block;margin-left:6px;}}
    [data-testid="stForm"]{{
        background:{t['card']};border:1px solid {t['border']};
        border-radius:14px;padding:20px 24px;
    }}
    [data-testid="stDataFrame"]{{border-radius:12px;overflow:hidden;}}
    </style>
    """, unsafe_allow_html=True)


inject_css()


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def page_header(icon, title, sub=""):
    st.markdown(
        f"<div class='page-title'>"
        f"<span style='font-size:1.8rem'>{icon}</span>"
        f"<div><h2>{title}</h2>{'<p>'+sub+'</p>' if sub else ''}</div>"
        f"</div>",
        unsafe_allow_html=True
    )


def section(label):
    st.markdown(f"<div class='sec'>{label}</div>", unsafe_allow_html=True)


def render_slot_map(location_id):
    data  = api_slots(location_id)
    slots = data.get("slots", [])
    queue = data.get("queue", [])
    if not slots:
        st.info("No slot data.")
        return

    free = sum(1 for s in slots if not s["is_occupied"])
    occ  = sum(1 for s in slots if s["is_occupied"])
    total = len(slots)
    pct   = int((occ / total) * 100) if total else 0
    bar_c = "danger" if pct >= 80 else ("warn" if pct >= 50 else "")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🟢 Free", free)
    c2.metric("🔴 Occupied", occ)
    c3.metric("📦 Total", total)
    c4.metric("⏳ Queue", len(queue))

    st.markdown(
        f"<div style='font-size:.78rem;color:#64748b;margin:8px 0 2px'>"
        f"Occupancy — {pct}%</div>"
        f"<div class='occ-bar-wrap'>"
        f"<div class='occ-bar {bar_c}' style='width:{pct}%'></div></div>",
        unsafe_allow_html=True
    )

    cols_per_row = 5
    for row_start in range(0, len(slots), cols_per_row):
        row_slots = slots[row_start: row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, slot in zip(cols, row_slots):
            with col:
                if slot["is_occupied"]:
                    st.markdown(
                        f"<div class='slot-occ'>"
                        f"<div class='slot-num'>SLOT #{slot['slot_number']}</div>"
                        f"<div class='slot-lbl'>🔴 {slot['vehicle_plate']}</div>"
                        f"<div class='slot-sub'>{slot['vehicle_owner']}</div>"
                        f"</div>", unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<div class='slot-free'>"
                        f"<div class='slot-num'>SLOT #{slot['slot_number']}</div>"
                        f"<div class='slot-lbl'>🟢 FREE</div>"
                        f"<div class='slot-sub'>Available</div>"
                        f"</div>", unsafe_allow_html=True
                    )

    if queue:
        section("⏳ Waiting Queue (FIFO)")
        st.dataframe(pd.DataFrame([{
            "#":       i + 1,
            "Plate":   v["vehicle_plate"],
            "Owner":   v["vehicle_owner"],
            "Queued":  str(v["queued_at"])[:16] if v.get("queued_at") else "—",
        } for i, v in enumerate(queue)]),
            use_container_width=True, hide_index=True
        )
    else:
        st.markdown(
            "<div style='color:#475569;font-size:.85rem;margin-top:8px'>"
            "No vehicles in queue ✅</div>",
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:16px 0 8px'>
      <div style='font-size:2.2rem'>🅿</div>
      <div style='font-size:1.2rem;font-weight:800;color:#3b82f6'>SmartPark</div>
      <div style='font-size:.75rem;color:#475569;margin-top:2px'>Smart Parking System</div>
    </div>
    """, unsafe_allow_html=True)

    # Backend status
    backend_ok = api_health()
    status_color = "#22c55e" if backend_ok else "#ef4444"
    status_label = "Backend Online ✅" if backend_ok else "Backend Offline ❌"
    st.markdown(
        f"<div style='text-align:center;font-size:.75rem;"
        f"color:{status_color};margin-bottom:8px'>{status_label}</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<hr style='border-color:#1e3a5f;margin:8px 0'/>",
        unsafe_allow_html=True
    )

    # Theme toggle
    t = get_theme()
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(
            "<div style='color:#94a3b8;font-size:.8rem;padding-top:8px'>"
            "🎨 Theme</div>",
            unsafe_allow_html=True
        )
    with col2:
        if st.button(f"{t['mode_icon']}", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.markdown(
        "<hr style='border-color:#1e3a5f;margin:8px 0 14px'/>",
        unsafe_allow_html=True
    )

    if st.session_state.logged_in:
        st.markdown(
            f"<div style='background:#0d2137;border:1px solid #1e3a5f;"
            f"border-radius:10px;padding:10px 14px;margin-bottom:14px'>"
            f"👤 <strong style='color:#60a5fa'>{st.session_state.username}</strong>"
            f"<div style='color:#475569;font-size:.75rem'>Logged in</div>"
            f"</div>",
            unsafe_allow_html=True
        )
        if st.button("🚪 Logout", use_container_width=True):
            for k in ["logged_in", "username", "token"]:
                st.session_state[k] = "" if k != "logged_in" else False
            st.rerun()

        st.markdown(
            "<div style='font-size:.72rem;color:#475569;text-transform:uppercase;"
            "letter-spacing:.1em;margin:10px 0 6px'>Menu</div>",
            unsafe_allow_html=True
        )
        page = st.radio("", [
            "📊  Dashboard",
            "🗺  Locations",
            "💰  Price Comparison",
            "🚗  Park Vehicle",
            "💳  Check Out",
            "🔍  Search Vehicle",
            "📡  Nearby Lots",
            "📋  Booking History",
            "📈  Analytics",
        ], label_visibility="collapsed")
    else:
        page = st.radio(
            "", ["🔑  Login", "📝  Register"],
            label_visibility="collapsed"
        )

    st.markdown(
        "<hr style='border-color:#1e3a5f;margin:14px 0 8px'/>"
        "<div style='font-size:.7rem;color:#334155;text-align:center'>"
        "FastAPI · Streamlit · MongoDB</div>",
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════
#  PAGE: LOGIN
# ══════════════════════════════════════════════════════════════
if page == "🔑  Login":
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
        <div class='auth-banner'>
          <div style='font-size:2.5rem'>🅿</div>
          <div class='auth-title'>SmartPark</div>
          <div class='auth-sub'>Sign in to your account</div>
        </div>
        """, unsafe_allow_html=True)
        with st.form("login_form"):
            username  = st.text_input("👤 Username")
            password  = st.text_input("🔒 Password", type="password")
            submitted = st.form_submit_button(
                "Sign In →", use_container_width=True, type="primary"
            )
        if submitted:
            ok, token, info = api_login(username, password)
            if ok:
                st.session_state.logged_in = True
                st.session_state.token     = token
                st.session_state.username  = info   # info = username on success
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error(f"❌ {info}")   # info = error message on failure


# ══════════════════════════════════════════════════════════════
#  PAGE: REGISTER
# ══════════════════════════════════════════════════════════════
elif page == "📝  Register":
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
        <div class='auth-banner'>
          <div style='font-size:2.5rem'>📝</div>
          <div class='auth-title'>Create Account</div>
          <div class='auth-sub'>Join SmartPark today</div>
        </div>
        """, unsafe_allow_html=True)
        with st.form("reg_form"):
            username  = st.text_input("👤 Username")
            password  = st.text_input("🔒 Password", type="password")
            confirm   = st.text_input("🔒 Confirm Password", type="password")
            submitted = st.form_submit_button(
                "Create Account →", use_container_width=True, type="primary"
            )
        if submitted:
            ok, msg = api_register(username, password, confirm)
            if ok:
                st.success(f"✅ {msg} → Switch to Login.")
            else:
                st.error(f"❌ {msg}")


# ══════════════════════════════════════════════════════════════
#  GUARD
# ══════════════════════════════════════════════════════════════
elif not st.session_state.logged_in:
    st.warning("Please login first.")
    st.stop()


# ══════════════════════════════════════════════════════════════
#  PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════
elif page == "📊  Dashboard":
    page_header("📊", "Dashboard",
                f"Welcome back, {st.session_state.username}")
    stats = api_stats()
    if stats:
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("📍 Locations",  stats.get("locations", 0))
        c2.metric("🟢 Free",       stats.get("free", 0))
        c3.metric("🔴 Occupied",   stats.get("occupied", 0))
        c4.metric("⏳ Queue",      stats.get("queued", 0))
        c5.metric("👤 Users",      stats.get("users", 0))
        c6.metric("📋 Bookings",   stats.get("bookings", 0))

    section("🗺 Locations Overview")
    locs = api_locations()
    if locs:
        for loc in locs:
            pct = int((loc["occupied"] / loc["total_slots"]) * 100) \
                  if loc.get("total_slots") else 0
            bar = "danger" if pct >= 80 else ("warn" if pct >= 50 else "")
            avail_cls = "avail-yes" if loc["free_slots"] > 0 else "avail-no"
            avail_lbl = f"✅ {loc['free_slots']} free" \
                        if loc["free_slots"] > 0 else "❌ Full"
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f"<strong style='color:#f1f5f9'>{loc['name']}</strong>"
                    f"<span class='rate-chip' style='margin-left:10px'>"
                    f"₹{loc['rate_per_hour']:.0f}/hr</span>"
                    f"<span class='avail-chip {avail_cls}' style='margin-left:8px'>"
                    f"{avail_lbl}</span>"
                    f"<div style='font-size:.8rem;color:#475569;margin:4px 0 4px'>"
                    f"📍 {loc['address']}</div>"
                    f"<div class='occ-bar-wrap'>"
                    f"<div class='occ-bar {bar}' style='width:{pct}%'></div></div>",
                    unsafe_allow_html=True
                )
            with col2:
                st.metric("", f"{pct}% full")

    section("🗺 Quick Slot Map")
    loc_map = {l["name"]: l["location_id"] for l in locs}
    if loc_map:
        chosen = st.selectbox(
            "Select location", list(loc_map.keys()),
            label_visibility="collapsed"
        )
        render_slot_map(loc_map[chosen])


# ══════════════════════════════════════════════════════════════
#  PAGE: LOCATIONS
# ══════════════════════════════════════════════════════════════
elif page == "🗺  Locations":
    page_header("🗺", "Parking Locations")
    locs = api_locations()
    for loc in locs:
        pct = int((loc["occupied"] / loc["total_slots"]) * 100) \
              if loc.get("total_slots") else 0
        bar = "danger" if pct >= 80 else ("warn" if pct >= 50 else "")
        with st.expander(
            f"📍 {loc['name']}  ·  ₹{loc['rate_per_hour']:.0f}/hr  ·  "
            f"🟢 {loc['free_slots']} free  ·  "
            f"🔴 {loc['occupied']} occ  ·  ⏳ {loc['queue_count']} queue"
        ):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Address:** {loc['address']}")
            c2.write(f"**Total Slots:** {loc['total_slots']}")
            c3.write(f"**Rate:** ₹{loc['rate_per_hour']:.2f}/hr")
            st.markdown(
                f"<div class='occ-bar-wrap'>"
                f"<div class='occ-bar {bar}' style='width:{pct}%'></div></div>"
                f"<div style='font-size:.75rem;color:#475569;margin-bottom:10px'>"
                f"Occupancy: {pct}%</div>",
                unsafe_allow_html=True
            )
            if st.button("View Slot Map", key=f"map_{loc['location_id']}"):
                st.session_state.active_loc = loc["location_id"]
            if st.session_state.active_loc == loc["location_id"]:
                render_slot_map(loc["location_id"])


# ══════════════════════════════════════════════════════════════
#  PAGE: PRICE COMPARISON
# ══════════════════════════════════════════════════════════════
elif page == "💰  Price Comparison":
    page_header("💰", "Price Comparison",
                "Compare rates across all locations")
    section("⏱ Select Duration")
    col1, col2 = st.columns(2)
    with col1:
        custom_h = st.slider("Duration (hours)", 1, 24, 3)
    with col2:
        st.markdown("<br/>", unsafe_allow_html=True)
        show_all = st.checkbox("Show 1/3/6/12/24h breakdown", value=True)

    hours_list = [1, 3, 6, 12, 24] if show_all else [custom_h]
    resp       = api_compare_prices(hours_list)

    if resp:
        price_data = resp.get("locations", [])
        cheapest   = resp.get("cheapest", {})

        est = cheapest.get(f"{custom_h}h",
              cheapest.get("rate_per_hour", 30) * custom_h)

        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#052e16,#0d1f1a);
                    border:1px solid #166534;border-radius:14px;
                    padding:18px 24px;margin:16px 0 24px;
                    display:flex;align-items:center;gap:16px'>
          <span style='font-size:2rem'>🏆</span>
          <div>
            <div style='font-size:.75rem;color:#6ee7b7;
                        text-transform:uppercase;letter-spacing:.1em'>
              Cheapest Available
            </div>
            <div style='font-size:1.2rem;font-weight:800;color:#f1f5f9;margin:4px 0'>
              {cheapest.get('name','—')}
            </div>
            <div style='font-size:.85rem;color:#94a3b8'>
              📍 {cheapest.get('address','—')} &nbsp;·&nbsp;
              <strong style='color:#22c55e'>
                ₹{cheapest.get('rate_per_hour',0):.0f}/hr
              </strong> &nbsp;·&nbsp;
              🟢 {cheapest.get('free_slots',0)} slots free
            </div>
          </div>
          <div style='margin-left:auto;text-align:right'>
            <div style='color:#94a3b8;font-size:.8rem'>
              For {custom_h} hour(s)
            </div>
            <div style='font-size:1.6rem;font-weight:800;color:#22c55e'>
              ₹{est:.2f}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        section("📊 All Locations — Rate Comparison")
        hour_headers = "".join(f"<th>{h}h Est.</th>" for h in hours_list)
        rows_html    = ""
        for loc in price_data:
            is_cheapest = loc["location_id"] == cheapest.get("location_id")
            avail_cls   = "avail-yes" if loc["free_slots"] > 0 else "avail-no"
            avail_lbl   = f"✅ {loc['free_slots']} free" \
                          if loc["free_slots"] > 0 else "❌ Full"
            best_badge  = "<span class='best-badge'>BEST</span>" if is_cheapest else ""
            row_cls     = "cheapest" if is_cheapest else ""
            hour_cells  = "".join(
                f"<td style='font-weight:{'800' if h==custom_h else '400'};'>"
                f"₹{loc.get(f'{h}h', 0):.2f}</td>"
                for h in hours_list
            )
            rows_html += f"""
            <tr class='{row_cls}'>
              <td><strong>{loc['name']}</strong>{best_badge}<br/>
                  <span style='font-size:.75rem;color:#475569'>
                    📍 {loc['address']}</span></td>
              <td><span class='rate-chip'>₹{loc['rate_per_hour']:.0f}/hr</span></td>
              <td><span class='avail-chip {avail_cls}'>{avail_lbl}</span></td>
              <td style='color:#64748b'>{loc['queue_count']} waiting</td>
              {hour_cells}
            </tr>"""

        st.markdown(
            f"<div style='background:#0d1117;border:1px solid #1e3a5f;"
            f"border-radius:14px;overflow:hidden'>"
            f"<table class='price-table'><thead><tr>"
            f"<th>Location</th><th>Rate</th><th>Availability</th>"
            f"<th>Queue</th>{hour_headers}</tr></thead>"
            f"<tbody>{rows_html}</tbody></table></div>",
            unsafe_allow_html=True
        )

        section("📈 Rate Visual")
        chart_df = pd.DataFrame({
            "Location":   [l["name"] for l in price_data],
            "₹ per hour": [l["rate_per_hour"] for l in price_data],
        })
        st.bar_chart(chart_df.set_index("Location"))


# ══════════════════════════════════════════════════════════════
#  PAGE: PARK VEHICLE
# ══════════════════════════════════════════════════════════════
elif page == "🚗  Park Vehicle":
    page_header("🚗", "Park Vehicle", "Assign slot & see fee instantly")
    locs    = api_locations()
    vtypes  = api_vehicle_types()
    loc_opts = {
        f"{l['name']}  —  ₹{l['rate_per_hour']:.0f}/hr  —  "
        f"{l['free_slots']} free": l for l in locs
    }
    vtype_opts = {
        f"{v.get('icon','🚗')} {v['type_name']} — ₹{v['rate_per_hour']:.0f}/hr": v
        for v in vtypes
    } if vtypes else {"🚗 Car — ₹30/hr": {"type_name": "Car", "rate_per_hour": 30}}

    col_form, col_info = st.columns([1.2, 1])
    with col_form:
        with st.form("park_form"):
            section("📋 Vehicle Details")
            chosen_loc   = st.selectbox("Parking Location", list(loc_opts.keys()))
            plate        = st.text_input(
                "License Plate", placeholder="e.g. KA01AB1234", max_chars=20
            ).upper()
            owner        = st.text_input("Owner Name", placeholder="Full name")
            chosen_vtype = st.selectbox("🚘 Vehicle Type", list(vtype_opts.keys()))
            section("⏱ Estimate Charge")
            est_hours = st.slider("Expected duration (hours)", 1, 24, 2)

            sel_loc   = loc_opts[chosen_loc]
            sel_vtype = vtype_opts[chosen_vtype]
            est_rate  = sel_vtype["rate_per_hour"]
            est_val   = max(1, est_hours) * est_rate

            st.markdown(
                f"<div style='background:linear-gradient(135deg,#0c1f3f,#111827);"
                f"border:1px solid #1e40af;border-radius:12px;"
                f"padding:14px 18px;margin-top:8px'>"
                f"<div style='font-size:.75rem;color:#64748b;margin-bottom:8px'>"
                f"💰 Estimated Fee</div>"
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center'>"
                f"<div style='font-size:.88rem;color:#94a3b8'>"
                f"{sel_vtype.get('icon','🚗')} {sel_vtype['type_name']} &nbsp;·&nbsp;"
                f"₹{est_rate:.0f}/hr &nbsp;·&nbsp; {est_hours} hr</div>"
                f"<div style='font-size:1.6rem;font-weight:900;color:#22c55e'>"
                f"₹{est_val:.2f}</div></div></div>",
                unsafe_allow_html=True
            )
            submitted = st.form_submit_button(
                "🅿 Park Vehicle", use_container_width=True, type="primary"
            )

        if submitted and plate and owner:
            ok, resp = api_park(
                sel_loc["location_id"], plate, owner,
                sel_vtype["type_name"]
            )
            if ok:
                if resp["status"] == "parked":
                    st.success(
                        f"✅ {resp['message']}"
                    )
                    st.markdown(
                        f"<div class='bill-card'>"
                        f"<div class='bill-title'>🧾 Parking Receipt</div>"
                        f"<div class='bill-row'><span>Vehicle</span>"
                        f"<strong>{plate}</strong></div>"
                        f"<div class='bill-row'><span>Slot</span>"
                        f"<strong>#{resp['slot']}</strong></div>"
                        f"<div class='bill-row'><span>Rate</span>"
                        f"<strong>₹{est_rate:.0f}/hr</strong></div>"
                        f"<div class='bill-total'>"
                        f"<span class='lbl'>Est. Charge</span>"
                        f"<span class='amt'>₹{est_val:.2f}</span></div>"
                        f"<div style='text-align:center;color:#475569;"
                        f"font-size:.75rem;margin-top:12px'>"
                        f"Actual charge at checkout</div></div>",
                        unsafe_allow_html=True
                    )
                    st.balloons()
                else:
                    st.warning(f"⏳ {resp['message']}")
            else:
                st.error(f"❌ {resp}")

    with col_info:
        section("💰 All Location Rates")
        price_resp = api_compare_prices([est_hours])
        if price_resp:
            cheapest = price_resp.get("cheapest", {})
            for loc in price_resp.get("locations", []):
                is_best   = loc["location_id"] == cheapest.get("location_id")
                avail_cls = "avail-yes" if loc["free_slots"] > 0 else "avail-no"
                border    = "#22c55e" if is_best else "#1e3a5f"
                badge     = "<span class='best-badge'>CHEAPEST</span>" \
                            if is_best else ""
                st.markdown(
                    f"<div style='background:#0d1117;border:1px solid {border};"
                    f"border-radius:10px;padding:12px 16px;margin-bottom:10px'>"
                    f"<div style='display:flex;justify-content:space-between;"
                    f"align-items:center'>"
                    f"<strong style='color:#f1f5f9;font-size:.92rem'>"
                    f"{loc['name']}</strong>{badge}</div>"
                    f"<div style='font-size:.8rem;color:#475569;margin:3px 0 8px'>"
                    f"📍 {loc['address']}</div>"
                    f"<div style='display:flex;gap:14px;font-size:.82rem'>"
                    f"<span class='rate-chip'>₹{loc['rate_per_hour']:.0f}/hr</span>"
                    f"<span class='avail-chip {avail_cls}'>"
                    f"{'✅ '+str(loc['free_slots'])+' free' if loc['free_slots'] > 0 else '❌ Full'}"
                    f"</span></div></div>",
                    unsafe_allow_html=True
                )


# ══════════════════════════════════════════════════════════════
#  PAGE: CHECK OUT
# ══════════════════════════════════════════════════════════════
elif page == "💳  Check Out":
    page_header("💳", "Check Out Vehicle", "Calculate actual parking bill")
    locs     = api_locations()
    loc_opts = {l["name"]: l for l in locs}

    col_form, col_info = st.columns([1.2, 1])
    with col_form:
        with st.form("checkout_form"):
            chosen = st.selectbox("Location", list(loc_opts.keys()))
            plate  = st.text_input(
                "License Plate", placeholder="e.g. KA01AB1234", max_chars=20
            ).upper()
            submitted = st.form_submit_button(
                "💳 Check Out & Calculate Bill",
                use_container_width=True, type="primary"
            )
        if submitted and plate:
            sel_loc = loc_opts[chosen]
            ok, resp = api_checkout(sel_loc["location_id"], plate)
            if ok:
                st.success("✅ Checked out!")
                st.markdown(
                    f"<div class='bill-card'>"
                    f"<div class='bill-title'>🧾 Final Bill</div>"
                    f"<div class='bill-row'><span>Vehicle</span>"
                    f"<strong>{resp['plate']}</strong></div>"
                    f"<div class='bill-row'><span>Location</span>"
                    f"<strong>{chosen}</strong></div>"
                    f"<div class='bill-row'><span>Slot</span>"
                    f"<strong>#{resp['slot']}</strong></div>"
                    f"<div class='bill-total'>"
                    f"<span class='lbl'>Total</span>"
                    f"<span class='amt'>₹{resp['charge']:.2f}</span></div>"
                    f"<div style='text-align:center;color:#475569;"
                    f"font-size:.75rem;margin-top:12px'>"
                    f"Thank you for using SmartPark! 🙏</div></div>",
                    unsafe_allow_html=True
                )
                if resp.get("auto_assigned"):
                    st.info(
                        f"ℹ️ Next queued vehicle "
                        f"**{resp['auto_assigned']}** auto-assigned to "
                        f"Slot #{resp['slot']}."
                    )
            else:
                st.error(f"❌ {resp}")

    with col_info:
        section("💡 Rate Info")
        for loc in locs:
            st.markdown(
                f"<div style='background:#0d1117;border:1px solid #1e3a5f;"
                f"border-radius:10px;padding:10px 14px;margin-bottom:8px;"
                f"font-size:.85rem'>"
                f"<strong style='color:#f1f5f9'>{loc['name']}</strong><br/>"
                f"<span class='rate-chip' style='margin-top:5px;display:inline-block'>"
                f"₹{loc['rate_per_hour']:.0f}/hr</span></div>",
                unsafe_allow_html=True
            )


# ══════════════════════════════════════════════════════════════
#  PAGE: SEARCH
# ══════════════════════════════════════════════════════════════
elif page == "🔍  Search Vehicle":
    page_header("🔍", "Search Vehicle")
    col_s, _ = st.columns([1.5, 1])
    with col_s:
        with st.form("search_form"):
            plate     = st.text_input(
                "License Plate", placeholder="e.g. KA01AB1234", max_chars=20
            ).upper()
            submitted = st.form_submit_button(
                "🔍 Search", use_container_width=True, type="primary"
            )
    if submitted and plate:
        results = api_search(plate)
        if not results:
            st.markdown(
                f"<div style='background:#1a0f00;border:1px solid #92400e;"
                f"border-radius:12px;padding:20px 24px;text-align:center;"
                f"color:#f59e0b'>⚠️ No vehicle found with plate "
                f"<strong>{plate}</strong></div>",
                unsafe_allow_html=True
            )
        for r in results:
            if r["status"] == "parked":
                st.markdown(
                    f"<div style='background:#0d1f1a;border:1px solid #166534;"
                    f"border-left:4px solid #22c55e;border-radius:12px;"
                    f"padding:16px 20px;margin-bottom:12px'>"
                    f"<div style='font-weight:700;margin-bottom:10px;color:#f1f5f9'>"
                    f"🟢 PARKED — {r['vehicle_plate']}</div>"
                    f"<div style='display:grid;grid-template-columns:1fr 1fr;"
                    f"gap:6px 20px;font-size:.88rem'>"
                    f"<span style='color:#64748b'>Location</span>"
                    f"<strong style='color:#f1f5f9'>{r['location_name']}</strong>"
                    f"<span style='color:#64748b'>Slot</span>"
                    f"<strong style='color:#22c55e'>#{r['slot_number']}</strong>"
                    f"<span style='color:#64748b'>Entry</span>"
                    f"<strong style='color:#f1f5f9'>{str(r.get('entry_time',''))[:16]}</strong>"
                    f"<span style='color:#64748b'>Charge So Far</span>"
                    f"<strong style='color:#22c55e;font-size:1.1rem'>"
                    f"₹{r.get('charge_so_far',0):.2f}</strong>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='background:#1a1500;border:1px solid #92400e;"
                    f"border-left:4px solid #f59e0b;border-radius:12px;"
                    f"padding:16px 20px;margin-bottom:12px'>"
                    f"<div style='font-weight:700;margin-bottom:10px;color:#f1f5f9'>"
                    f"⏳ IN QUEUE — {r['vehicle_plate']}</div>"
                    f"<div style='font-size:.88rem'>"
                    f"<span style='color:#64748b'>Location: </span>"
                    f"<strong style='color:#f1f5f9'>{r['location_name']}</strong><br/>"
                    f"<span style='color:#64748b'>Queued At: </span>"
                    f"<strong style='color:#f1f5f9'>"
                    f"{str(r.get('queued_at',''))[:16]}</strong></div></div>",
                    unsafe_allow_html=True
                )


# ══════════════════════════════════════════════════════════════
#  PAGE: NEARBY
# ══════════════════════════════════════════════════════════════
elif page == "📡  Nearby Lots":
    page_header("📡", "Nearby Lots")
    c1, c2, c3 = st.columns(3)
    with c1: lat    = st.number_input("Latitude",  value=12.9716, format="%.6f")
    with c2: lon    = st.number_input("Longitude", value=77.5946, format="%.6f")
    with c3: radius = st.slider("Radius (km)", 1, 20, 5)

    if st.button("📡 Find Nearby", type="primary"):
        results = api_nearby(lat, lon, radius)
        if not results:
            st.info(f"No lots within {radius} km.")
        else:
            st.success(f"Found {len(results)} location(s)")
            for loc in results:
                pct = int((loc["occupied"] / loc["total_slots"]) * 100) \
                      if loc.get("total_slots") else 0
                bar = "danger" if pct >= 80 else ("warn" if pct >= 50 else "")
                st.markdown(
                    f"<div style='background:#111827;border:1px solid #1e3a5f;"
                    f"border-left:4px solid #3b82f6;border-radius:12px;"
                    f"padding:16px 20px;margin-bottom:12px'>"
                    f"<strong style='color:#f1f5f9;font-size:1.05rem'>"
                    f"{loc['name']}</strong><br/>"
                    f"<div style='font-size:.84rem;color:#64748b;margin:4px 0 10px'>"
                    f"📍 {loc['address']}</div>"
                    f"<div style='display:flex;gap:18px;font-size:.84rem;flex-wrap:wrap'>"
                    f"<span>📏 <strong>{loc['distance_km']} km</strong></span>"
                    f"<span class='rate-chip'>₹{loc['rate_per_hour']:.0f}/hr</span>"
                    f"<span style='color:#22c55e'>🟢 {loc['free_slots']} free</span>"
                    f"<span style='color:#ef4444'>🔴 {loc['occupied']} occ</span>"
                    f"</div>"
                    f"<div class='occ-bar-wrap' style='margin-top:10px'>"
                    f"<div class='occ-bar {bar}' style='width:{pct}%'></div></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )


# ══════════════════════════════════════════════════════════════
#  PAGE: BOOKINGS
# ══════════════════════════════════════════════════════════════
elif page == "📋  Booking History":
    page_header("📋", "Booking History")
    c1, c2 = st.columns([2, 1])
    with c1: mine  = st.toggle("Only my bookings", value=False)
    with c2: limit = st.selectbox("Show last", [25, 50, 100], index=0)

    records = api_bookings(mine=mine, limit=limit)
    if not records:
        st.info("No bookings found.")
    else:
        df = pd.DataFrame([{
            "Date":      str(r.get("booked_at", ""))[:16],
            "User":      r.get("user_id", "—"),
            "Location":  r.get("location_name", "—"),
            "Plate":     r.get("vehicle_plate", "—"),
            "Slot":      f"#{r['slot_number']}" if r.get("slot_number") else "Queue",
            "Checked Out": str(r.get("checked_out_at", ""))[:16] or "🟢 Active",
            "Charge (₹)": f"₹{r['charge']:.2f}" if r.get("charge") else "—",
        } for r in records])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(records)} records")


# ══════════════════════════════════════════════════════════════
#  PAGE: ANALYTICS
# ══════════════════════════════════════════════════════════════
elif page == "📈  Analytics":
    page_header("📈", "Analytics Dashboard")
    try:
        import plotly.express as px
        data = api_analytics()
        if not data:
            st.info("No analytics data yet.")
            st.stop()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Total Revenue",   f"₹{data.get('total_revenue',0):.2f}")
        k2.metric("📅 Today's Revenue", f"₹{data.get('today_revenue',0):.2f}")
        k3.metric("⏱ Avg Duration",     f"{data.get('avg_duration',0)} hrs")
        k4.metric("📊 Bookings Data",   "Live")

        section("📅 Last 7 Days")
        col1, col2 = st.columns(2)
        daily = data.get("daily", [])
        if daily:
            df_d = pd.DataFrame(daily)
            df_d["day"] = df_d["day"].astype(str)
            with col1:
                fig = px.bar(df_d, x="day", y="revenue",
                             title="Daily Revenue (₹)",
                             color_discrete_sequence=["#3b82f6"])
                fig.update_layout(
                    plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                    font_color="#94a3b8", title_font_color="#f1f5f9",
                    margin=dict(t=40,b=20,l=10,r=10)
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig2 = px.line(df_d, x="day", y="total_bookings",
                               title="Daily Bookings", markers=True)
                fig2.update_layout(
                    plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                    font_color="#94a3b8", title_font_color="#f1f5f9",
                    margin=dict(t=40,b=20,l=10,r=10)
                )
                fig2.update_traces(
                    line_color="#22c55e", marker_color="#22c55e"
                )
                st.plotly_chart(fig2, use_container_width=True)

        section("🚘 Vehicle Types & Peak Hours")
        col3, col4 = st.columns(2)
        vtype_all = data.get("vtype_all", [])
        if vtype_all:
            with col3:
                df_v = pd.DataFrame(vtype_all)
                fig3 = px.pie(df_v, names="vehicle_type", values="total",
                              title="Vehicle Distribution", hole=0.45,
                              color_discrete_sequence=px.colors.sequential.Blues_r)
                fig3.update_layout(
                    plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                    font_color="#94a3b8", title_font_color="#f1f5f9",
                    margin=dict(t=40,b=20,l=10,r=10)
                )
                st.plotly_chart(fig3, use_container_width=True)

        peak = data.get("peak_hours", [])
        if peak:
            with col4:
                df_p = pd.DataFrame(peak)
                df_p["hour"] = df_p["hour"].apply(lambda h: f"{int(h):02d}:00")
                fig4 = px.bar(df_p, x="hour", y="bookings",
                              title="Peak Hours",
                              color="bookings",
                              color_continuous_scale="Oranges")
                fig4.update_layout(
                    plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                    font_color="#94a3b8", title_font_color="#f1f5f9",
                    coloraxis_showscale=False,
                    margin=dict(t=40,b=20,l=10,r=10)
                )
                st.plotly_chart(fig4, use_container_width=True)

        section("📍 Per Location Revenue")
        loc_stats = data.get("loc_stats", [])
        if loc_stats:
            st.dataframe(pd.DataFrame([{
                "Location":      l["name"],
                "Rate/hr":       f"₹{l['rate_per_hour']:.0f}",
                "Occupied 🔴":  l["occupied"],
                "Free 🟢":      l["free"],
                "Revenue":       f"₹{l['total_revenue']:.2f}",
            } for l in loc_stats]),
                use_container_width=True, hide_index=True
            )

    except ImportError:
        st.error("Install plotly: `pip install plotly`")
    except Exception as e:
        st.error(f"Analytics error: {e}")
