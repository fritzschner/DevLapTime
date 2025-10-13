import streamlit as st
import pandas as pd
from datetime import datetime
import os

DATEIPFAD = "rundenzeiten.txt"

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
    df = pd.read_csv(DATEIPFAD, sep="\t")
    return df

def speichere_zeiten(df):
    df.to_csv(DATEIPFAD, sep="\t", index=False)

def main():
    st.title("RaceKino Rundenzeiten")

    df = lade_zeiten()

    # Eingabeformular
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
            return

    if not df.empty:
        st.subheader("Alle erfassten Zeiten")
        df["Nr."] = df.index + 1

        for idx, row in df.iterrows():
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
                if st.button("Löschen", key=f"del_{idx}"):
                    df = df.drop(idx).reset_index(drop=True)
                    speichere_zeiten(df)
                    st.experimental_rerun()
                    return

        # Durchschnitt der besten 3 Zeiten pro Fahrer
        rangliste = []
        for name, gruppe in df.groupby("Fahrer"):
            beste3 = gruppe["Zeit (s)"].nsmallest(3)
            if len(beste3) == 3:
                avg = beste3.mean()
                rangliste.append({
                    "Fahrer": name,
                    "Durchschnitt (Top 3)": sekunden_zu_zeitstr(avg)
                })

        if rangliste:
            rang_df = pd.DataFrame(rangliste).sort_values("Durchschnitt (Top 3)").reset_index(drop=True)
            rang_df["Platz"] = rang_df.index + 1  # Platzierung ab 1

            st.subheader("Aktuelle Rangliste (Top 3 Zeiten)")

            # Darstellung mit Hervorhebung der Top 3
            for idx, row in rang_df.iterrows():
                platz = row["Platz"]
                fahrer = row["Fahrer"]
                zeit = row["Durchschnitt (Top 3)"]

                # Farben für die ersten drei Plätze
                if platz == 1:
                    style = "background-color:#FFD700; font-weight:bold;"  # Gold
                elif platz == 2:
                    style = "background-color:#C0C0C0; font-weight:bold;"  # Silber
                elif platz == 3:
                    style = "background-color:#CD7F32; font-weight:bold;"  # Bronze
                else:
                    style = ""

                st.markdown(
                    f"<div style='padding:4px; margin-bottom:2px; {style}'>"
                    f"<span style='font-size:18px;'><b>{platz}.</b></span> "
                    f"<span style='font-size:18px;'><b>{fahrer}</b></span> – "
                    f"<span style='font-size:18px;'><b>{zeit}</b></span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Mindestens ein Fahrer braucht 3 Zeiten für die Rangliste.")
    else:
        st.info("Bitte gib die ersten Zeiten ein.")

if __name__ == "__main__":
    main()
