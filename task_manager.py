import streamlit as st
import pandas as pd
import os
from datetime import date, datetime

# ── Konfigurace stránky ──────────────────────────────────────────────────────
st.set_page_config(page_title="Můj Planner", page_icon="✅", layout="centered")

st.markdown("""
<style>
    .stApp { max-width: 700px; margin: auto; }
    .task-done { text-decoration: line-through; opacity: 0.5; }
    div[data-testid="stExpander"] { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ── Soubor pro uložení úkolů ─────────────────────────────────────────────────
DATA_FILE = "ukoly.csv"

def nacti_ukoly():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["deadline"] = pd.to_datetime(df["deadline"]).dt.date
        return df
    return pd.DataFrame(columns=["ukol", "priorita", "deadline", "hotovo", "vytvoreno"])

def uloz_ukoly(df):
    df.to_csv(DATA_FILE, index=False)

# ── Načtení dat ──────────────────────────────────────────────────────────────
if "ukoly" not in st.session_state:
    st.session_state.ukoly = nacti_ukoly()

df = st.session_state.ukoly

# ── Hlavička ─────────────────────────────────────────────────────────────────
st.title("✅ Můj Planner")
st.caption(f"Dnes je {datetime.now().strftime('%A %d. %B %Y')}")

dnes = date.today()
celkem = len(df)
hotovo = int(df["hotovo"].sum()) if celkem > 0 else 0
aktivni = celkem - hotovo
po_deadlinu = int(((df["deadline"] < dnes) & (~df["hotovo"].astype(bool))).sum()) if celkem > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Aktivní úkoly", aktivni)
col2.metric("Splněno", hotovo)
col3.metric("Po deadlinu", po_deadlinu, delta=None if po_deadlinu == 0 else f"⚠️ {po_deadlinu}", delta_color="inverse")

st.divider()

# ── Přidat nový úkol ─────────────────────────────────────────────────────────
with st.expander("➕ Přidat nový úkol", expanded=(celkem == 0)):
    with st.form("novy_ukol", clear_on_submit=True):
        nazev = st.text_input("Název úkolu", placeholder="Co je potřeba udělat?")
        col_a, col_b = st.columns(2)
        priorita = col_a.selectbox("Priorita", ["🔴 Vysoká", "🟡 Střední", "🟢 Nízká"])
        deadline = col_b.date_input("Deadline", value=dnes)
        odeslano = st.form_submit_button("Přidat úkol", use_container_width=True, type="primary")

        if odeslano and nazev.strip():
            novy = pd.DataFrame([{
                "ukol": nazev.strip(),
                "priorita": priorita,
                "deadline": deadline,
                "hotovo": False,
                "vytvoreno": datetime.now().strftime("%Y-%m-%d %H:%M")
            }])
            st.session_state.ukoly = pd.concat([df, novy], ignore_index=True)
            uloz_ukoly(st.session_state.ukoly)
            st.success(f"Ukol '{nazev}' pridan!")
            st.rerun()
        elif odeslano:
            st.warning("Zadej prosím název úkolu.")

# ── Filtrování ───────────────────────────────────────────────────────────────
if celkem > 0:
    st.subheader("📋 Úkoly")

    zobrazit = st.radio(
        "Zobrazit",
        ["Aktivní", "Splněné", "Vše"],
        horizontal=True,
        label_visibility="collapsed"
    )

    df_view = st.session_state.ukoly.copy()

    if zobrazit == "Aktivní":
        df_view = df_view[~df_view["hotovo"].astype(bool)]
    elif zobrazit == "Splněné":
        df_view = df_view[df_view["hotovo"].astype(bool)]

    # Seřazení: priorita pak deadline
    priorita_poradi = {"🔴 Vysoká": 0, "🟡 Střední": 1, "🟢 Nízká": 2}
    df_view["_por"] = df_view["priorita"].map(priorita_poradi)
    df_view = df_view.sort_values(["hotovo", "_por", "deadline"]).reset_index(drop=False)

    if df_view.empty:
        st.info("Žádné úkoly k zobrazení.")
    else:
        for _, row in df_view.iterrows():
            orig_idx = row["index"]
            po_deadlinu_flag = (row["deadline"] < dnes) and not row["hotovo"]

            col_check, col_info, col_del = st.columns([0.08, 0.82, 0.10])

            with col_check:
                hotovo_now = st.checkbox(
                    "",
                    value=bool(row["hotovo"]),
                    key=f"check_{orig_idx}"
                )
                if hotovo_now != bool(row["hotovo"]):
                    st.session_state.ukoly.at[orig_idx, "hotovo"] = hotovo_now
                    uloz_ukoly(st.session_state.ukoly)
                    st.rerun()

            with col_info:
                nazev_styl = f'<span class="task-done">{row["ukol"]}</span>' if row["hotovo"] else f'<b>{row["ukol"]}</b>'
                deadline_str = row["deadline"].strftime("%d. %m. %Y")
                barva = "#e74c3c" if po_deadlinu_flag else "#888"
                deadline_label = f'<span style="color:{barva}; font-size:0.85em;">⏰ {deadline_str}{"  ⚠️ po deadlinu" if po_deadlinu_flag else ""}</span>'
                st.markdown(
                    f'{nazev_styl} &nbsp; {row["priorita"]}<br>{deadline_label}',
                    unsafe_allow_html=True
                )

            with col_del:
                if st.button("🗑️", key=f"del_{orig_idx}", help="Smazat úkol"):
                    st.session_state.ukoly = st.session_state.ukoly.drop(index=orig_idx).reset_index(drop=True)
                    uloz_ukoly(st.session_state.ukoly)
                    st.rerun()

    # ── Export ───────────────────────────────────────────────────────────────
    st.divider()
    csv_export = st.session_state.ukoly.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Stáhnout úkoly jako CSV",
        data=csv_export,
        file_name="moje_ukoly.csv",
        mime="text/csv",
        use_container_width=True
    )
else:
    st.info("Zatím žádné úkoly. Přidej první pomocí formuláře výše! 👆")
