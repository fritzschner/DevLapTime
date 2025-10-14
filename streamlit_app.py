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
        return pd.DataFrame(columns=["Fahrer", "Minuten", "Sekunden", "Tausendstel", "Zeit (s)", "Zeitstr", "Erfasst am", "Event"])
    return pd.read_csv(DATEIPFAD, sep=";")

def speichere_zeiten(df):
    df.to_csv(DATEIPFAD, sep=";", index=False)

# ------------------- Hauptfunktion -------------------
def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", layout="wide")

    # Farbdesign & Überschrift
    st.markdown("""
    <style>
    body { background-color: #0e0e0e; color: white; }
    .block-container { max-width: 1100px; margin: auto; }
    .title {
        background-color: #c20000; color: white; text-align: center;
        padding: 15px; border-radius: 12px; font-size: 32px; font-weight: bold; margin-bottom: 25px;
    }
    .ranking-entry { padding: 8px; margin-bottom: 4px; border-radius: 8px; }
    .gold { background-color: #FFD700CC; color: black; }
    .silver { background-color: #C0C0C0CC; color: black; }
    .bronze { background-color: #CD7F32CC; color: white; }
    .time-box { background-color: #1b1b1b; padding: 10px; border-radius: 8px; margin-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="title">🏁 RaceKino Rundenzeiten</div>', unsafe_allow_html=True)

    df = lade_zeiten()

    # ---------------- Event Filter ----------------
    vorhandene_events = sorted(df["Event"].dropna().unique()) if not df.empty else []
    if "event_neu" not in st.session_state:
        st.session_state["event_neu"] = ""

    col_event1, col_event2 = st.columns([3, 2])
    event_filter = col_event1.selectbox(
        "🔹 Wähle ein Event",
        options=vorhandene_events + ([st.session_state["event_neu"]] if st.session_state["event_neu"] else []),
        index=0 if vorhandene_events else -1,
        key="event_auswahl"
    )
    col_event2.text_input("Neues Event hinzufügen", key="event_neu")

    # ---------------- Eingabeformular ----------------
    st.subheader("🏎️ Neue Rundenzeit eintragen")

    if not st.session_state.get("zeit_input_temp"):
        st.session_state["zeit_input_temp"] = ""

    col1, col2 = st.columns([2, 2])
    fahrer = col1.text_input("Fahrername", key="fahrername")
    raw_input = col2.text_input(
        "6 Ziffern eingeben (Format: MSSTTT)",
        value=st.session_state["zeit_input_temp"],
        max_chars=6,
        key="zeit_input_field"
    )

    # Live-Formatierung der Eingabe
    if raw_input:
        clean = "".join(filter(str.isdigit, raw_input))
        formatted_input = ""
        if len(clean) >= 1:
            formatted_input += clean[0] + ":"
        if len(clean) >= 3:
            formatted_input += clean[1:3] + "."
        if len(clean) > 3:
            formatted_input += clean[3:6]
        st.markdown(f"🕒 **Eingegebene Zeit:** {formatted_input}")

    # Speichern-Button
    if st.button("💾 Hinzufügen", use_container_width=True):
        if not event_filter:
            st.warning("Bitte wähle zuerst ein Event aus.")
        elif not fahrer:
            st.warning("Bitte Fahrername eingeben.")
        elif not raw_input.isdigit() or len(raw_input) != 6:
            st.warning("Bitte genau 6 Ziffern eingeben (Format M SS MMM).")
        else:
            try:
                minuten = int(raw_input[0])
                sekunden = int(raw_input[1:3])
                tausendstel = int(raw_input[3:6])
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
                        "Erfasst am": jetzt,
                        "Event": event_filter
                    }])
                    df = pd.concat([df, neue_zeile], ignore_index=True)
                    speichere_zeiten(df)
                    st.session_state["zeit_input_temp"] = ""
                    st.success(f"✅ Zeit für {fahrer} unter Event '{event_filter}' gespeichert!")
            except Exception as e:
                st.error(f"Fehler beim Verarbeiten der Eingabe: {e}")

    # ---------------- Rangliste ----------------
    if not df.empty and event_filter:
        df_event = df[df["Event"] == event_filter]
        rangliste = []
        for name, gruppe in df_event.groupby("Fahrer"):
            beste3 = gruppe["Zeit (s)"].nsmallest(3)
            if len(beste3) == 3:
                avg = beste3.mean()
                rangliste.append({
                    "Fahrer": name,
                    "Durchschnitt (Top 3)": sekunden_zu_zeitstr(avg),
                    "Wert": avg
                })
        if rangliste:
            st.subheader(f"🏆 Rangliste für Event: {event_filter}")
            rang_df = pd.DataFrame(rangliste).sort_values("Wert").reset_index(drop=True)
            rang_df["Platz"] = rang_df.index + 1
            for _, row in rang_df.iterrows():
                style = "gold" if row["Platz"] == 1 else "silver" if row["Platz"] == 2 else "bronze" if row["Platz"] == 3 else ""
                st.markdown(
                    f'<div class="ranking-entry {style}">'
                    f'<b>{row["Platz"]}. {row["Fahrer"]}</b> – {row["Durchschnitt (Top 3)"]}'
                    f'</div>', unsafe_allow_html=True
                )
            csv_rang = rang_df[["Platz", "Fahrer", "Durchschnitt (Top 3)"]].to_csv(index=False, sep=";").encode("utf-8")
            st.download_button("📥 Rangliste als CSV", csv_rang, "rangliste.csv", "text/csv", use_container_width=True)
        else:
            st.info("Mindestens ein Fahrer braucht 3 Zeiten für die Rangliste.")

    # ---------------- Letzte 10 Rundenzeiten ----------------
    if not df.empty and event_filter:
        st.subheader(f"⏱️ Letzte 10 Rundenzeiten für Event: {event_filter}")
        df_event = df[df["Event"] == event_filter]
        fahrer_filter = st.multiselect("Filter nach Fahrer:", options=sorted(df_event["Fahrer"].unique()), default=None)
        sortierung = st.radio("Sortierung:", ["Neueste Einträge zuerst", "Schnellste Zeiten zuerst"], horizontal=True)
        df_filtered = df_event[df_event["Fahrer"].isin(fahrer_filter)] if fahrer_filter else df_event
        df_anzeige = df_filtered.sort_values("Erfasst am", ascending=False) if sortierung=="Neueste Einträge zuerst" else df_filtered.sort_values("Zeit (s)", ascending=True)
        df_anzeige = df_anzeige.head(10)

        for idx, row in df_anzeige.iterrows():
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(
                    f'<div class="time-box">'
                    f'<b>{row["Fahrer"]}</b> – <i>{row["Event"]}</i><br>'
                    f'⏱️ {row["Zeitstr"]} <span style="color:gray;font-size:12px;">({row["Erfasst am"]})</span>'
                    f'</div>', unsafe_allow_html=True
                )
            with col2:
                if st.button("🗑️", key=f"del_{row.name}", help="Diesen Eintrag löschen"):
                    df = df.drop(row.name).reset_index(drop=True)
                    speichere_zeiten(df)
                    st.success("✅ Eintrag gelöscht!")

        col_a, col_b = st.columns(2)
        with col_a:
            csv_zeiten = df_event.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button("📥 Alle Zeiten als CSV", csv_zeiten, "rundenzeiten.csv", "text/csv", use_container_width=True)

        with col_b:
            if st.session_state.get("show_delete_all_confirm") is None:
                st.session_state["show_delete_all_confirm"] = False
            if not st.session_state["show_delete_all_confirm"]:
                if st.button("🗑️ Alle Rundenzeiten für Event löschen", use_container_width=True):
                    st.session_state["show_delete_all_confirm"] = True
            else:
                st.warning("⚠️ Willst du wirklich alle Zeiten für dieses Event löschen?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("🗑️ Ja, löschen", key="delete_all_confirm", use_container_width=True):
                        df = df[df["Event"] != event_filter]
                        speichere_zeiten(df)
                        st.session_state["show_delete_all_confirm"] = False
                        st.success("🗑️ Alle Zeiten für Event gelöscht.")
                with col_no:
                    if st.button("❌ Abbrechen", key="cancel_delete_all", use_container_width=True):
                        st.session_state["show_delete_all_confirm"] = False
                        st.info("Löschvorgang abgebrochen.")
    else:
        st.info("Noch keine Rundenzeiten erfasst oder kein Event ausgewählt.")

# ------------------- Start -------------------
if __name__ == "__main__":
    main()
