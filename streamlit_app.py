import streamlit as st
import pandas as pd
from datetime import datetime
import os

DATEIPFAD = "rundenzeiten.csv"

# ------------------- Hilfsfunktionen -------------------
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
    return pd.read_csv(DATEIPFAD, sep=";")

def speichere_zeiten(df):
    df.to_csv(DATEIPFAD, sep=";", index=False)

# ------------------- Hauptfunktion -------------------
def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", layout="wide")

    # Farbdesign & Überschrift
    st.markdown(
        """
        <style>
        body {
            background-color: #0e0e0e;
            color: white;
        }
        .block-container {
            max-width: 1100px;
            margin: auto;
        }
        .title {
            background-color: #c20000;
            color: white;
            text-align: center;
            padding: 15px;
            border-radius: 12px;
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 25px;
        }
        .ranking-entry {
            padding: 8px;
            margin-bottom: 4px;
            border-radius: 8px;
        }
        .gold { background-color: #FFD70033; }
        .silver { background-color: #C0C0C033; }
        .bronze { background-color: #CD7F3233; }
        .time-box {
            background-color: #1b1b1b;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="title">🏁 RaceKino Rundenzeiten</div>', unsafe_allow_html=True)

    df = lade_zeiten()

    # ---------------- Eingabeformular ----------------
    with st.form("eingabe_formular"):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        fahrer = col1.text_input("Fahrername")
        minuten = col2.number_input("Minuten", min_value=0, max_value=59, step=1, format="%d")
        sekunden = col3.number_input("Sekunden", min_value=0, max_value=59, step=1, format="%d")
        tausendstel = col4.number_input("Tausendstel", min_value=0, max_value=999, step=1, format="%03d")
        abgeschickt = st.form_submit_button("💾 Hinzufügen", use_container_width=True)

        if abgeschickt and fahrer and (minuten > 0 or sekunden > 0 or tausendstel > 0):
            zeit_in_sek = zeit_zu_sekunden(minuten, sekunden, tausendstel)
            jetzt = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            zeitstr = f"{int(minuten)}:{int(sekunden):02d}:{int(tausendstel):03d}"
            neue_zeile = pd.DataFrame([{
                "Fahrer": fahrer,
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

    # ---------------- Rangliste ----------------
    if not df.empty:
        rangliste = []
        for name, gruppe in df.groupby("Fahrer"):
            beste3 = gruppe["Zeit (s)"].nsmallest(3)
            if len(beste3) == 3:
                avg = beste3.mean()
                rangliste.append({
                    "Fahrer": name,
                    "Durchschnitt (Top 3)": sekunden_zu_zeitstr(avg),
                    "Wert": avg
                })

        if rangliste:
            st.subheader("🏆 Aktuelle Rangliste (Top 3 Zeiten)")
            rang_df = pd.DataFrame(rangliste).sort_values("Wert").reset_index(drop=True)
            rang_df["Platz"] = rang_df.index + 1

            for _, row in rang_df.iterrows():
                style = ""
                if row["Platz"] == 1:
                    style = "gold"
                elif row["Platz"] == 2:
                    style = "silver"
                elif row["Platz"] == 3:
                    style = "bronze"

                st.markdown(
                    f'<div class="ranking-entry {style}">'
                    f'<b>{row["Platz"]}. {row["Fahrer"]}</b> – {row["Durchschnitt (Top 3)"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            csv_rang = rang_df[["Platz", "Fahrer", "Durchschnitt (Top 3)"]].to_csv(index=False, sep=";").encode("utf-8")
            st.download_button("📥 Rangliste als CSV", csv_rang, "rangliste.csv", "text/csv", use_container_width=True)

        else:
            st.info("Mindestens ein Fahrer braucht 3 Zeiten für die Rangliste.")

    # ---------------- Letzte Zeiten ----------------
    if not df.empty:
        st.subheader("⏱️ Letzte 10 Rundenzeiten")

        sortierung = st.radio(
            "Sortierung:",
            ["Neueste Einträge zuerst", "Schnellste Zeiten zuerst"],
            horizontal=True,
        )

        if sortierung == "Neueste Einträge zuerst":
            df_anzeige = df.sort_values("Erfasst am", ascending=False)
        else:
            df_anzeige = df.sort_values("Zeit (s)", ascending=True)

        df_anzeige = df_anzeige.head(10).reset_index(drop=True)
        df_anzeige["Nr."] = df_anzeige.index + 1

        for _, row in df_anzeige.iterrows():
            st.markdown(
                f'<div class="time-box">'
                f'<b>{row["Nr."]}. {row["Fahrer"]}</b><br>'
                f'⏱️ {row["Zeitstr"]} <span style="color:gray;font-size:12px;">({row["Erfasst am"]})</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # CSV-Export + Alle löschen
        col_a, col_b = st.columns(2)
        with col_a:
            csv_zeiten = df.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button("📥 Alle Zeiten als CSV", csv_zeiten, "rundenzeiten.csv", "text/csv", use_container_width=True)
        with col_b:
            if st.button("🗑️ Alle Zeiten löschen", use_container_width=True, type="secondary"):
                os.remove(DATEIPFAD)
                st.warning("Alle Zeiten wurden gelöscht.")
                st.rerun()
    else:
        st.info("Noch keine Rundenzeiten erfasst.")

# ------------------- Start -------------------
if __name__ == "__main__":
    main()
