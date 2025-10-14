import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

DATEIPFAD = "rundenzeiten.csv"

# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------

def lade_zeiten():
    if not os.path.exists(DATEIPFAD):
        return pd.DataFrame(columns=["Fahrer", "Event", "Minuten", "Sekunden", "Tausendstel", "Zeit (s)", "Zeitstr", "Erfasst am"])
    df = pd.read_csv(DATEIPFAD, sep=";")
    # Sicherstellen, dass alle Spalten vorhanden sind
    for col in ["Fahrer", "Event", "Minuten", "Sekunden", "Tausendstel", "Zeit (s)", "Zeitstr", "Erfasst am"]:
        if col not in df.columns:
            df[col] = ""
    return df

def speichere_zeit(fahrer, event, minuten, sekunden, tausendstel):
    df = lade_zeiten()
    try:
        zeit_s = int(minuten) * 60 + int(sekunden) + int(tausendstel) / 1000
        zeit_str = f"{int(minuten):02}:{int(sekunden):02}.{int(tausendstel):03}"
        neuer_eintrag = pd.DataFrame([{
            "Fahrer": fahrer,
            "Event": event,
            "Minuten": minuten,
            "Sekunden": sekunden,
            "Tausendstel": tausendstel,
            "Zeit (s)": zeit_s,
            "Zeitstr": zeit_str,
            "Erfasst am": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        df = pd.concat([df, neuer_eintrag], ignore_index=True)
        df.to_csv(DATEIPFAD, sep=";", index=False)
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")
        return False

def loesche_alle_zeiten():
    if os.path.exists(DATEIPFAD):
        os.remove(DATEIPFAD)

# ------------------------------------------------------------
# Streamlit App
# ------------------------------------------------------------

def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", layout="centered")
    st.title("🏁 RaceKino Rundenzeiten")

    df = lade_zeiten()

    # Fahrer- und Eventauswahl (mit vorhandenen Werten aus CSV)
    fahrer_optionen = sorted(df["Fahrer"].dropna().unique()) if not df.empty else []
    event_optionen = sorted(df["Event"].dropna().unique()) if not df.empty else []

    # Eingabebereich ---------------------------------------------------
    with st.form("eingabe_form"):
        col1, col2 = st.columns(2)
        with col1:
            fahrer = st.text_input("Fahrername eingeben oder auswählen:", value="", placeholder="z. B. Max", key="fahrer_input")
            if fahrer_optionen:
                fahrer = st.selectbox("Oder Fahrer auswählen:", [""] + fahrer_optionen, index=0, key="fahrer_select") or st.session_state.fahrer_input
        with col2:
            event = st.text_input("Event eingeben oder auswählen:", value="", placeholder="z. B. Qualifying 1", key="event_input")
            if event_optionen:
                event = st.selectbox("Oder Event auswählen:", [""] + event_optionen, index=0, key="event_select") or st.session_state.event_input

        col3, col4, col5 = st.columns(3)
        with col3:
            minuten = st.text_input("Minuten", placeholder="mm", key="minuten")
        with col4:
            sekunden = st.text_input("Sekunden", placeholder="ss", key="sekunden")
        with col5:
            tausendstel = st.text_input("Tausendstel", placeholder="xxx", key="tausendstel")

        submitted = st.form_submit_button("💾 Zeit speichern")

        if submitted:
            if fahrer and event and minuten and sekunden and tausendstel:
                if speichere_zeit(fahrer, event, minuten, sekunden, tausendstel):
                    st.success("✅ Zeit erfolgreich gespeichert!")
                    # Eingabefelder zurücksetzen
                    for key in ["fahrer_input", "event_input", "minuten", "sekunden", "tausendstel"]:
                        st.session_state[key] = ""
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Bitte alle Felder ausfüllen!")

    st.markdown("---")

    # Filterbereich ---------------------------------------------------
    if not df.empty:
        selected_event = st.selectbox("🔍 Event auswählen (Filter):", ["Alle"] + sorted(df["Event"].dropna().unique()))
        if selected_event != "Alle":
            df = df[df["Event"] == selected_event]

        st.subheader("🏆 Letzte 10 Rundenzeiten")
        df_anzeige = df.sort_values(by="Zeit (s)").head(10)
        st.dataframe(df_anzeige[["Fahrer", "Event", "Zeitstr", "Erfasst am"]])

        # Lösch-Button mit Bestätigung
        if st.button("🗑️ Alle Rundenzeiten löschen"):
            with st.modal("⚠️ Bestätigung erforderlich"):
                st.warning("Willst du wirklich **alle Zeiten** löschen? Diese Aktion kann nicht rückgängig gemacht werden.")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Ja, löschen"):
                        loesche_alle_zeiten()
                        st.success("Alle Zeiten wurden gelöscht.")
                        time.sleep(1)
                        st.rerun()
                with col_no:
                    if st.button("❌ Abbrechen"):
                        st.info("Löschvorgang abgebrochen.")
                        st.rerun()
    else:
        st.info("Noch keine Rundenzeiten vorhanden.")

# ------------------------------------------------------------
# Startpunkt
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
