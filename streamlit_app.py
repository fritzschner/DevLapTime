import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time

DATEIPFAD = "rundenzeiten.csv"

# ------------------- Hilfsfunktionen -------------------
def zeit_zu_sekunden(minuten, sekunden, tausendstel):
    return minuten * 60 + sekunden + tausendstel / 1000

def sekunden_zu_zeitstr(sekunden):
    minuten = int(sekunden // 60)
    rest = sekunden % 60
    sek = int(rest)
    tausendstel = int(round((rest - sek) * 1000))
    return f"{minuten}:{sek:02d}.{tausendstel:03d}"

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
        col1, col2 = st.columns([2, 2])
        fahrer = col1.text_input("Fahrername")

        with col2:
            st.markdown("**Rundenzeit eingeben (ohne Trennzeichen):**")
            zeit_input = st.text_input("z. B. 125512 → 1:25.512 oder 059123 → 0:59.123", max_chars=6)

            # Live-Vorschau der interpretierten Zeit
            if zeit_input.isdigit() and len(zeit_input) == 6:
                minuten = int(zeit_input[0])
                sekunden = int(zeit_input[1:3])
                tausendstel = int(zeit_input[3:6])
                if sekunden <= 59 and tausendstel <= 999:
                    st.markdown(f"🕒 **Eingegebene Zeit:** {minuten}:{sekunden:02d}.{tausendstel:03d}")
                else:
                    st.markdown("<span style='color:#ff6666;'>❌ Ungültige Kombination (Sekunden ≤ 59, Tausendstel ≤ 999)</span>", unsafe_allow_html=True)
            elif len(zeit_input) > 0:
                st.markdown("<span style='color:#888;'>Bitte genau 6 Ziffern eingeben (Format M SS MMM)</span>", unsafe_allow_html=True)

        abgeschickt = st.form_submit_button("💾 Hinzufügen", use_container_width=True)

        if abgeschickt:
            if not fahrer:
                st.warning("Bitte Fahrername eingeben.")
            elif not zeit_input.isdigit():
                st.warning("Bitte nur Zahlen eingeben (z. B. 125512).")
            elif len(zeit_input) != 6:
                st.warning("Bitte genau 6 Ziffern eingeben (Format M SS MMM).")
            else:
                try:
                    minuten = int(zeit_input[0])
                    sekunden = int(zeit_input[1:3])
                    tausendstel = int(zeit_input[3:6])

                    if sekunden > 59 or tausendstel > 999:
                        st.error("Ungültige Zeit. Sekunden ≤ 59, Tausendstel ≤ 999.")
                    else:
                        zeit_in_sek = zeit_zu_sekunden(minuten, sekunden, tausendstel)
                        jetzt = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                        zeitstr = f"{minuten}:{sekunden:02d}.{tausendstel:03d}"

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

                except Exception as e:
                    st.error(f"Fehler beim Verarbeiten der Eingabe: {e}")

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

    # ---------------- Filter und letzte Zeiten ----------------
    if not df.empty:
        st.subheader("⏱️ Letzte 10 Rundenzeiten")

        # Fahrer-Filter
        fahrer_filter = st.multiselect(
            "Filter nach Fahrer:",
            options=sorted(df["Fahrer"].unique()),
            default=None
        )

        # Sortierung
        sortierung = st.radio(
            "Sortierung:",
            ["Neueste Einträge zuerst", "Schnellste Zeiten zuerst"],
            horizontal=True,
        )

        # Gefiltertes DataFrame
        df_filtered = df[df["Fahrer"].isin(fahrer_filter)] if fahrer_filter else df

        if sortierung == "Neueste Einträge zuerst":
            df_anzeige = df_filtered.sort_values("Erfasst am", ascending=False)
        else:
            df_anzeige = df_filtered.sort_values("Zeit (s)", ascending=True)

        df_anzeige = df_anzeige.head(10)  # letzte 10 Einträge

        for idx, row in df_anzeige.iterrows():
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(
                    f'<div class="time-box">'
                    f'<b>{row["Fahrer"]}</b><br>'
                    f'⏱️ {row["Zeitstr"]} <span style="color:gray;font-size:12px;">({row["Erfasst am"]})</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("🗑️", key=f"del_{row.name}", help="Diesen Eintrag löschen"):
                    df = df.drop(row.name).reset_index(drop=True)
                    speichere_zeiten(df)
                    st.success("✅ Eintrag gelöscht.")
                    time.sleep(1)
                    st.rerun()

        # CSV-Export + Alle löschen
        col_a, col_b = st.columns(2)
        with col_a:
            csv_zeiten = df.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button("📥 Alle Zeiten als CSV", csv_zeiten, "rundenzeiten.csv", "text/csv", use_container_width=True)
        with col_b:
            if st.button("🗑️ Alle Zeiten löschen", use_container_width=True, type="secondary"):
                os.remove(DATEIPFAD)
                st.error("🗑️ Alle Zeiten gelöscht.")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Noch keine Rundenzeiten erfasst.")

# ------------------- Start -------------------
if __name__ == "__main__":
    main()
