import streamlit as st
import pandas as pd
from datetime import datetime
import os

DATEIPFAD = "rundenzeiten.csv"

# ---------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------

def zeit_zu_sekunden(minuten, sekunden, tausendstel):
    return minuten * 60 + sekunden + tausendstel / 1000

def sekunden_zu_zeitstr(sekunden):
    minuten = int(sekunden // 60)
    rest = sekunden % 60
    sek = int(rest)
    tausendstel = int(round((rest - sek) * 1000))
    return f"{minuten}:{sek:02d}:{tausendstel:03d}"

def lade_zeiten():
    if not os.path.exists(DATEIPFAD):
        return pd.DataFrame(columns=["Fahrer", "Minuten", "Sekunden", "Tausendstel", "Zeit (s)", "Zeitstr", "Erfasst am"])
    try:
        df = pd.read_csv(DATEIPFAD, sep=";", encoding="utf-8")
    except Exception:
        df = pd.DataFrame(columns=["Fahrer", "Minuten", "Sekunden", "Tausendstel", "Zeit (s)", "Zeitstr", "Erfasst am"])
    return df

def speichere_zeiten(df):
    df.to_csv(DATEIPFAD, sep=";", index=False, encoding="utf-8")

# ---------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------

def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", page_icon="🏁", layout="wide")

    # -----------------------------------------------------------
    # Stil & Layout (modernes schwarz-rotes Theme)
    # -----------------------------------------------------------
    st.markdown(
        """
        <style>
        body {
            background-color: #0d0d0d;
            color: #fff;
            font-family: 'Roboto', sans-serif;
        }
        .main {
            background-color: #0d0d0d;
        }
        .title-red {
            background-color: #e53935;
            color: white;
            padding: 10px;
            border-radius: 8px;
        }
        .stButton>button {
            background: linear-gradient(90deg, #e53935 0%, #b71c1c 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.6em 1.5em;
            font-weight: bold;
            font-size: 15px;
        }
        .stButton>button:hover {
            background: linear-gradient(90deg, #ff5252 0%, #c62828 100%);
        }
        div[data-testid="stForm"] {
            background-color: #1b1b1b;
            padding: 1.2em;
            border-radius: 10px;
            border: 1px solid #333;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<h1 class="title-red">🏁 RaceKino Rundenzeiten</h1>', unsafe_allow_html=True)

    df = lade_zeiten()
    df_full = df.copy()

    # -----------------------------------------------------------
    # Rangliste oben
    # -----------------------------------------------------------
    st.subheader("🏆 Aktuelle Rangliste (Top 3 Durchschnitt)")

    rangliste = []
    for name, gruppe in df_full.groupby("Fahrer"):
        beste3 = gruppe["Zeit (s)"].nsmallest(3)
        if len(beste3) == 3:
            avg = beste3.mean()
            rangliste.append({
                "Fahrer": name,
                "Durchschnitt (Top 3)": sekunden_zu_zeitstr(avg),
                "Wert (s)": avg
            })

    if rangliste:
        rang_df = pd.DataFrame(rangliste).sort_values("Wert (s)").reset_index(drop=True)
        rang_df["Platz"] = rang_df.index + 1

        col_dl1, col_dl2 = st.columns([1,1])  # Platz für Download-Button

        for _, row in rang_df.iterrows():
            platz = row["Platz"]
            fahrer = row["Fahrer"]
            zeit = row["Durchschnitt (Top 3)"]

            if platz == 1:
                style = "background-color:#FFD700;color:black;font-weight:bold;"
            elif platz == 2:
                style = "background-color:#C0C0C0;color:black;font-weight:bold;"
            elif platz == 3:
                style = "background-color:#CD7F32;color:white;font-weight:bold;"
            else:
                style = "background-color:#1b1b1b;color:white;"
            st.markdown(
                f"<div style='padding:8px;margin:4px;border-radius:8px;{style}'>"
                f"<span style='font-size:18px'><b>{platz}.</b> {fahrer} – {zeit}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        # Rangliste Download
        rang_df_export = rang_df[["Platz", "Fahrer", "Durchschnitt (Top 3)"]]
        col_dl2.download_button(
            "🏁 Rangliste herunterladen",
            data=rang_df_export.to_csv(sep=";", index=False).encode("utf-8"),
            file_name="rangliste.csv",
            mime="text/csv"
        )
    else:
        st.info("Mindestens ein Fahrer benötigt 3 Zeiten für die Rangliste.")

    st.divider()

    # -----------------------------------------------------------
    # Eingabeformular
    # -----------------------------------------------------------
    with st.form("eingabe_formular"):
        fahrer = st.text_input("Fahrername")
        col1, col2, col3 = st.columns(3)
        with col1:
            minuten = st.number_input("Minuten", min_value=0, max_value=59, step=1, format="%d")
        with col2:
            sekunden = st.number_input("Sekunden", min_value=0, max_value=59, step=1, format="%d")
        with col3:
            tausendstel = st.number_input("Tausendstel", min_value=0, max_value=999, step=1, format="%03d")
        abgeschickt = st.form_submit_button("Hinzufügen")

        if abgeschickt and fahrer and (minuten > 0 or sekunden > 0 or tausendstel > 0):
            zeit_in_sek = zeit_zu_sekunden(minuten, sekunden, tausendstel)
            jetzt = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            zeitstr = f"{int(minuten)}:{int(sekunden):02d}:{int(tausendstel):03d}"
            neue_zeile = pd.DataFrame([{
                "Fahrer": fahrer.strip(),
                "Minuten": minuten,
                "Sekunden": sekunden,
                "Tausendstel": tausendstel,
                "Zeit (s)": zeit_in_sek,
                "Zeitstr": zeitstr,
                "Erfasst am": jetzt
            }])
            df = pd.concat([df, neue_zeile], ignore_index=True)
            speichere_zeiten(df)
            st.rerun()
            return

    # -----------------------------------------------------------
    # Letzte 10 Rundenzeiten
    # -----------------------------------------------------------
    if not df.empty:
        st.subheader("⏱️ Letzte 10 schnellste Zeiten")

        suchtext = st.text_input("🔍 Fahrer filtern", placeholder="Name eingeben...")

        df_sorted = df.sort_values("Zeit (s)").reset_index(drop=True)
        if suchtext:
            df_sorted = df_sorted[df_sorted["Fahrer"].str.contains(suchtext, case=False, na=False)]

        df_view = df_sorted.head(10)

        df_view["Nr."] = range(1, len(df_view) + 1)
        for i, row in df_view.iterrows():
            col1, col2, col3, col4 = st.columns([1, 3, 4, 1])
            with col1:
                st.markdown(f"**{row['Nr.']}**")
            with col2:
                st.markdown(f"**{row['Fahrer']}**")
            with col3:
                st.markdown(
                    f"**{row['Zeitstr']}**  \n"
                    f"<span style='font-size:12px;color:gray;'>{row['Erfasst am']}</span>",
                    unsafe_allow_html=True
                )
            with col4:
                if st.button("Löschen", key=f"del_{i}"):
                    mask = (
                        (df_full["Fahrer"] == row["Fahrer"]) &
                        (df_full["Erfasst am"] == row["Erfasst am"]) &
                        (df_full["Zeitstr"] == row["Zeitstr"])
                    )
                    idx_to_del = df_full[mask].index
                    if not idx_to_del.empty:
                        df_full = df_full.drop(idx_to_del[0]).reset_index(drop=True)
                        speichere_zeiten(df_full)
                        st.rerun()
                        return

        st.divider()

        # -----------------------------------------------------------
        # Download & Alle löschen Buttons
        # -----------------------------------------------------------
        col_dl1, col_dl2, col_clear = st.columns([1,1,1])
        with col_dl1:
            st.download_button(
                "📄 Alle Zeiten herunterladen",
                data=df_full.to_csv(sep=";", index=False).encode("utf-8"),
                file_name="rundenzeiten_export.csv",
                mime="text/csv"
            )
        with col_dl2:
            pass
        with col_clear:
            if st.button("🚨 Alle Daten löschen"):
                sicher = st.checkbox("Ich bin sicher, dass ich alles löschen will.")
                if sicher:
                    os.remove(DATEIPFAD)
                    st.warning("Alle Zeiten wurden gelöscht!")
                    st.rerun()
                    return
    else:
        st.info("Bitte gib die ersten Zeiten ein.")

# ---------------------------------------------------------------
if __name__ == "__main__":
    main()
