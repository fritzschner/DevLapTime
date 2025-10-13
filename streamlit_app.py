import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# --------------------
# Konfiguration
# --------------------
DATEIPFAD = "rundenzeiten.csv"
CSV_SEP = ";"  # für Excel-kompatible CSV-Dateien

# --------------------
# Hilfsfunktionen
# --------------------
def zeit_zu_sekunden(minuten, sekunden, tausendstel):
    return minuten * 60 + sekunden + tausendstel / 1000

def sekunden_zu_zeitstr(sekunden):
    minuten = int(sekunden // 60)
    rest = sekunden % 60
    sek = int(rest)
    tausendstel = int(round((rest - sek) * 1000))
    if tausendstel >= 1000:
        tausendstel -= 1000
        sek += 1
    if sek >= 60:
        sek -= 60
        minuten += 1
    return f"{minuten}:{sek:02d}:{tausendstel:03d}"

def lade_zeiten():
    if not os.path.exists(DATEIPFAD):
        return pd.DataFrame(columns=["Fahrer", "Minuten", "Sekunden", "Tausendstel", "Zeit (s)", "Zeitstr", "Erfasst am"])
    df = pd.read_csv(DATEIPFAD, sep=CSV_SEP)
    df = df.fillna("")
    return df

def speichere_zeiten(df):
    df.to_csv(DATEIPFAD, sep=CSV_SEP, index=False)

def csv_bytes(df):
    with io.StringIO() as buffer:
        df.to_csv(buffer, sep=CSV_SEP, index=False)
        return buffer.getvalue().encode("utf-8")

# --------------------
# Streamlit Layout
# --------------------
st.set_page_config(page_title="RaceKino Rundenzeiten", layout="wide")
st.markdown(
    """
    <style>
    .rk-header {font-size:30px; font-weight:700; color:#fff; background-color:#b30000; padding:10px; border-radius:8px;}
    .rk-card {background-color:#1a1a1a; color:white; padding:8px 10px; border-radius:8px; margin-bottom:4px;}
    .rk-small {font-size:13px; color:gray;}
    .rk-gold {background-color:#FFD700; font-weight:bold; color:black;}
    .rk-silver {background-color:#C0C0C0; font-weight:bold; color:black;}
    .rk-bronze {background-color:#CD7F32; font-weight:bold; color:black;}
    </style>
    """, unsafe_allow_html=True
)
st.markdown('<div class="rk-header">🏁 RaceKino — Rundenzeiten</div>', unsafe_allow_html=True)

# --------------------
# Daten laden
# --------------------
df = lade_zeiten()

# --------------------
# Eingabeformular
# --------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Neue Zeit hinzufügen")

    with st.form("eingabe_form"):
        fahrer = st.text_input("Fahrername")
        c1, c2, c3 = st.columns(3)
        with c1:
            minuten = st.number_input("Minuten", 0, 59, 0, 1)
        with c2:
            sekunden = st.number_input("Sekunden", 0, 59, 0, 1)
        with c3:
            tausendstel = st.number_input("Tausendstel", 0, 999, 0, 1, format="%03d")

        abgeschickt = st.form_submit_button("Hinzufügen")

        if abgeschickt:
            if not fahrer.strip():
                st.warning("Bitte einen Fahrernamen eingeben.")
            elif minuten == sekunden == tausendstel == 0:
                st.warning("Zeit darf nicht 0:00:000 sein.")
            else:
                zeit_in_s = zeit_zu_sekunden(minuten, sekunden, tausendstel)
                zeitstr = f"{minuten}:{sekunden:02d}:{tausendstel:03d}"
                jetzt = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                neue_zeile = pd.DataFrame([{
                    "Fahrer": fahrer.strip(),
                    "Minuten": minuten,
                    "Sekunden": sekunden,
                    "Tausendstel": tausendstel,
                    "Zeit (s)": zeit_in_s,
                    "Zeitstr": zeitstr,
                    "Erfasst am": jetzt
                }])
                df = pd.concat([df, neue_zeile], ignore_index=True)
                speichere_zeiten(df)
                st.experimental_rerun()

    st.markdown("---")
    st.subheader("Aktionen")

    if st.button("🗑️ Alle Einträge löschen"):
        if st.checkbox("Ja, ich bin sicher – alles löschen"):
            df = pd.DataFrame(columns=df.columns)
            speichere_zeiten(df)
            st.success("Alle Daten wurden gelöscht.")
            st.experimental_rerun()

    st.markdown("---")

    if not df.empty:
        st.download_button("📥 Alle Zeiten herunterladen (CSV)", csv_bytes(df), "rundenzeiten.csv", "text/csv")

# --------------------
# Anzeige & Rangliste
# --------------------
with col2:
    st.subheader("Übersicht der letzten 10 Zeiten")

    if df.empty:
        st.info("Noch keine Zeiten erfasst.")
    else:
        # Filter & Sortierung
        filter_name = st.text_input("Filter: Fahrername (Teilstring)", "")

        df_view = df.copy()
        if filter_name.strip():
            df_view = df_view[df_view["Fahrer"].str.contains(filter_name.strip(), case=False, na=False)]

        # Nur die 10 neuesten (nach Erfasst am)
        try:
            df_view["Erfasst_sort"] = pd.to_datetime(df_view["Erfasst am"], format="%d.%m.%Y %H:%M:%S")
            df_view = df_view.sort_values("Erfasst_sort", ascending=False)
        except Exception:
            df_view = df_view.sort_values("Erfasst am", ascending=False)

        df_view = df_view.head(10).reset_index(drop=True)
        df_view.index = df_view.index + 1

        for i, row in df_view.iterrows():
            c1, c2, c3, c4 = st.columns([1, 3, 3, 1])
            with c1:
                st.markdown(f"**{i}.**")
            with c2:
                st.markdown(f"**{row['Fahrer']}**")
                st.markdown(f"<div class='rk-small'>{row['Erfasst am']}</div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div class='rk-card'>{row['Zeitstr']}</div>", unsafe_allow_html=True)
            with c4:
                if st.button("Löschen", key=f"del_{i}"):
                    mask = (
                        (df["Fahrer"] == row["Fahrer"]) &
                        (df["Erfasst am"] == row["Erfasst am"]) &
                        (df["Zeitstr"] == row["Zeitstr"])
                    )
                    idx_to_del = df[mask].index
                    if not idx_to_
