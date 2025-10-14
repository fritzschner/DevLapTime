import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# -------------------------------------------------
# 🔹 KONFIGURATION
# -------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=creds)

# Diese beiden IDs musst du nachher anpassen:
RUNDENZEITEN_FILE_ID = "1bzYUWbUPjyY_IJMjmzWp7J1_Ud2xyyji"
EVENTS_FILE_ID = "1XXZ8npAOg9h-AVpmpan2XgHmEHEbK99B"

# -------------------------------------------------
# 🔹 Hilfsfunktionen
# -------------------------------------------------
def zeit_zu_sekunden(minuten, sekunden, tausendstel):
    return minuten * 60 + sekunden + tausendstel / 1000

def sekunden_zu_zeitstr(sekunden):
    minuten = int(sekunden // 60)
    rest = sekunden % 60
    sek = int(rest)
    tausendstel = int(round((rest - sek) * 1000))
    return f"{minuten}:{sek:02d}.{tausendstel:03d}"

def lade_csv(file_id, spalten):
    """CSV von Google Drive laden"""
    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh, sep=";")
        for s in spalten:
            if s not in df.columns:
                df[s] = ""
        return df
    except Exception as e:
        st.warning(f"⚠️ Datei konnte nicht geladen werden: {e}")
        return pd.DataFrame(columns=spalten)

def speichere_csv(df, file_id):
    """CSV nach Google Drive hochladen (überschreiben)"""
    try:
        fh = io.BytesIO()
        df.to_csv(fh, sep=";", index=False)
        fh.seek(0)
        media = MediaIoBaseUpload(fh, mimetype="text/csv", resumable=True)
        drive_service.files().update(fileId=file_id, media_body=media).execute()
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern: {e}")

# -------------------------------------------------
# 🔹 Haupt-App
# -------------------------------------------------
def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", layout="wide")

    # ---- Design ----
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

    # ---- Daten laden ----
    df = lade_csv(RUNDENZEITEN_FILE_ID, ["Fahrer", "Minuten", "Sekunden", "Tausendstel",
                                         "Zeit (s)", "Zeitstr", "Erfasst am", "Event"])
    df_events = lade_csv(EVENTS_FILE_ID, ["Event"])
    vorhandene_events = sorted(df_events["Event"].dropna().unique()) if not df_events.empty else []

    if "event_neu" not in st.session_state:
        st.session_state["event_neu"] = ""

    # ---- Event-Auswahl ----
    col_event1, col_event2 = st.columns([3, 2])
    event_filter = col_event1.selectbox(
        "🔹 Wähle ein Event",
        options=vorhandene_events + ([st.session_state["event_neu"]] if st.session_state["event_neu"] else []),
        index=0 if vorhandene_events else -1,
        key="event_auswahl"
    )
    neues_event = col_event2.text_input("Neues Event hinzufügen", key="event_neu")

    if neues_event and st.button("➕ Event speichern", use_container_width=True):
        if neues_event not in vorhandene_events:
            df_events = pd.concat([df_events, pd.DataFrame([{"Event": neues_event}])], ignore_index=True)
            speichere_csv(df_events, EVENTS_FILE_ID)
            st.success(f"✅ Event '{neues_event}' gespeichert! Bitte Seite neu laden.")
        else:
            st.info("Event existiert bereits.")

    # ---- Zeiten-Eingabe ----
    st.subheader("🏎️ Neue Rundenzeit eintragen")

    fahrer = st.text_input("Fahrername")
    raw_input = st.text_input("6 Ziffern eingeben (Format: MSSTTT)", max_chars=6)

    if raw_input:
        clean = "".join(filter(str.isdigit, raw_input))
        formatted = ""
        if len(clean) >= 1:
            formatted += clean[0] + ":"
        if len(clean) >= 3:
            formatted += clean[1:3] + "."
        if len(clean) > 3:
            formatted += clean[3:6]
        st.markdown(f"🕒 **Eingegebene Zeit:** {formatted}")

    if st.button("💾 Hinzufügen", use_container_width=True):
        if not event_filter:
            st.warning("Bitte wähle zuerst ein Event aus.")
        elif not fahrer:
            st.warning("Bitte Fahrername eingeben.")
        elif not raw_input.isdigit() or len(raw_input) != 6:
            st.warning("Bitte genau 6 Ziffern eingeben (Format M SS MMM).")
        else:
            minuten = int(raw_input[0])
            sekunden = int(raw_input[1:3])
            tausendstel = int(raw_input[3:6])
            if sekunden > 59 or tausendstel > 999:
                st.error("Ungültige Zeit.")
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
                speichere_csv(df, RUNDENZEITEN_FILE_ID)
                st.success(f"✅ Zeit für {fahrer} unter Event '{event_filter}' gespeichert!")

    # ---- Rangliste ----
    if not df.empty and event_filter:
        df_event = df[df["Event"] == event_filter]
        rangliste = []
        for name, gruppe in df_event.groupby("Fahrer"):
            beste3 = gruppe["Zeit (s)"].nsmallest(3)
            if len(beste3) == 3:
                avg = beste3.mean()
                rangliste.append({"Fahrer": name, "Durchschnitt (Top 3)": sekunden_zu_zeitstr(avg), "Wert": avg})

        if rangliste:
            st.subheader(f"🏆 Rangliste für Event: {event_filter}")
            rang_df = pd.DataFrame(rangliste).sort_values("Wert").reset_index(drop=True)
            rang_df["Platz"] = rang_df.index + 1
            for _, row in rang_df.iterrows():
                style = "gold" if row["Platz"] == 1 else "silver" if row["Platz"] == 2 else "bronze" if row["Platz"] == 3 else ""
                st.markdown(f'<div class="ranking-entry {style}"><b>{row["Platz"]}. {row["Fahrer"]}</b> – {row["Durchschnitt (Top 3)"]}</div>', unsafe_allow_html=True)
        else:
            st.info("Mindestens 3 Zeiten pro Fahrer erforderlich.")

# -------------------------------------------------
if __name__ == "__main__":
    main()

import io
import os
import time
import pandas as pd
import streamlit as st
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# ============================================================
# GOOGLE DRIVE VERBINDUNG
# ============================================================
SCOPES = ["https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPES)
drive_service = build("drive", "v3", credentials=creds)

# ------------------------------------------------------------
# 📄 Datei-IDs (werden später ergänzt)
# ------------------------------------------------------------
RUNDEN_FILE_ID = "1bzYUWbUPjyY_IJMjmzWp7J1_Ud2xyyji"
EVENTS_FILE_ID = "1XXZ8npAOg9h-AVpmpan2XgHmEHEbK99B"

# ============================================================
# HILFSFUNKTIONEN GOOGLE DRIVE
# ============================================================
def lade_csv(file_id):
    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return pd.read_csv(fh, sep=";")
    except Exception:
        return pd.DataFrame(columns=["Fahrer", "Minuten", "Sekunden", "Tausendstel", "Zeit (s)", "Zeitstr", "Erfasst am", "Event"])

def speichere_csv(df, file_id):
    buffer = io.BytesIO()
    df.to_csv(buffer, sep=";", index=False)
    buffer.seek(0)
    media = MediaIoBaseUpload(buffer, mimetype="text/csv", resumable=True)
    drive_service.files().update(fileId=file_id, media_body=media).execute()

def lade_events(file_id):
    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return [e.strip() for e in fh.read().decode("utf-8").splitlines() if e.strip()]
    except Exception:
        return []

def speichere_events(event_liste, file_id):
    buffer = io.BytesIO("\n".join(event_liste).encode("utf-8"))
    media = MediaIoBaseUpload(buffer, mimetype="text/plain", resumable=True)
    drive_service.files().update(fileId=file_id, media_body=media).execute()

# ============================================================
# HILFSFUNKTIONEN ZEIT
# ============================================================
def zeit_zu_sekunden(minuten, sekunden, tausendstel):
    return minuten * 60 + sekunden + tausendstel / 1000

def sekunden_zu_zeitstr(sekunden):
    minuten = int(sekunden // 60)
    rest = sekunden % 60
    sek = int(rest)
    tausendstel = int(round((rest - sek) * 1000))
    return f"{minuten}:{sek:02d}.{tausendstel:03d}"

# ============================================================
# 🏁 HAUPTFUNKTION
# ============================================================
def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", layout="wide")

    # DESIGN ---------------------------------------------------
    st.markdown("""
        <style>
            body { background-color: #0e0e0e; color: white; }
            .block-container { max-width: 1100px; margin: auto; }
            .title { background-color: #c20000; color: white; text-align: center; padding: 15px; border-radius: 12px; font-size: 32px; font-weight: bold; margin-bottom: 25px; }
            .ranking-entry { padding: 8px; margin-bottom: 4px; border-radius: 8px; }
            .gold { background-color: #ffcc00aa; color: black; }
            .silver { background-color: #c0c0ffcc; color: black; }
            .bronze { background-color: #ff9933cc; color: white; }
            .time-box { background-color: #1b1b1b; padding: 10px; border-radius: 8px; margin-bottom: 8px; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="title">🏁 RaceKino Rundenzeiten</div>', unsafe_allow_html=True)

    # ============================================================
    # 📂 Daten laden
    # ============================================================
    df = lade_csv(RUNDEN_FILE_ID)
    events = lade_events(EVENTS_FILE_ID)

    # ============================================================
    # 🎯 Event-Auswahl
    # ============================================================
    st.subheader("🎟️ Event auswählen")
    selected_event = st.selectbox("Wähle ein Event:", options=events)

    if not selected_event:
        st.warning("Bitte zuerst ein Event auswählen oder unten ein neues Event anlegen.")
        st.stop()

    # ============================================================
    # 🏎️ Neue Rundenzeit eingeben
    # ============================================================
    st.subheader("🏎️ Neue Rundenzeit eintragen")

    if "zeit_input_temp" not in st.session_state:
        st.session_state["zeit_input_temp"] = ""

    col1, col2 = st.columns([2, 2])
    fahrer = col1.text_input("Fahrername", key="fahrername")
    raw_input = col2.text_input(
        "6 Ziffern eingeben (Format: MSSTTT)",
        value=st.session_state["zeit_input_temp"],
        max_chars=6,
        key="zeit_input_field"
    )

    # Liveformatierung
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

    if st.button("💾 Hinzufügen", use_container_width=True):
        if not fahrer:
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
                        "Event": selected_event
                    }])

                    df = pd.concat([df, neue_zeile], ignore_index=True)
                    speichere_csv(df, RUNDEN_FILE_ID)

                    st.session_state["zeit_input_temp"] = ""
                    st.success(f"✅ Zeit für {fahrer} gespeichert!")

            except Exception as e:
                st.error(f"Fehler beim Verarbeiten der Eingabe: {e}")

    # ============================================================
    # 🏆 Rangliste
    # ============================================================
    df_event = df[df["Event"] == selected_event]
    if not df_event.empty:
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
            st.subheader(f"🏆 Rangliste ({selected_event})")
            rang_df = pd.DataFrame(rangliste).sort_values("Wert").reset_index(drop=True)
            rang_df["Platz"] = rang_df.index + 1
            for _, row in rang_df.iterrows():
                style = "gold" if row["Platz"] == 1 else "silver" if row["Platz"] == 2 else "bronze" if row["Platz"] == 3 else ""
                st.markdown(
                    f'<div class="ranking-entry {style}">'
                    f'<b>{row["Platz"]}. {row["Fahrer"]}</b> – {row["Durchschnitt (Top 3)"]}'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # ============================================================
    # ⏱️ Letzte 10 Zeiten (gefiltert nach Event)
    # ============================================================
    st.subheader(f"⏱️ Letzte 10 Rundenzeiten ({selected_event})")
    df_event_sorted = df_event.sort_values("Erfasst am", ascending=False).head(10)
    for _, row in df_event_sorted.iterrows():
        st.markdown(
            f'<div class="time-box">'
            f'<b>{row["Fahrer"]}</b> – {row["Zeitstr"]} '
            f'<span style="color:gray;font-size:12px;">({row["Erfasst am"]})</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ============================================================
    # ➕ Neues Event anlegen
    # ============================================================
    st.subheader("➕ Neues Event hinzufügen")
    new_event = st.text_input("Eventname eingeben:")
    if st.button("📁 Event speichern"):
        if new_event and new_event not in events:
            events.append(new_event)
            speichere_events(events, EVENTS_FILE_ID)
            st.success("✅ Neues Event gespeichert! Bitte App neu laden.")
        else:
            st.warning("Eventname ist leer oder existiert bereits.")

# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    main()
    
