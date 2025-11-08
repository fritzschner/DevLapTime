import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# -------------------------------------------------
# 🔹 KONFIGURATION
# -------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=creds)

RUNDENZEITEN_FILE_ID = "1bzYUWbUPjyY_IJMjmzWp7J1_Ud2xyyji"
EVENTS_FILE_ID = "11WeEQCBk2tJ7jobGymiSTNNHWgdxV6Zv"
FAHRER_FILE_ID = "1d6zuytjCTGw8GUW7K7nOWgh4bi9XtaKp"
LOESCH_PASSWORT = "Olli071220"  # <-- hier dein gewünschtes Passwort

MEZ = pytz.timezone("Europe/Berlin")
SPALTEN = ["Fahrer", "Minuten", "Sekunden", "Tausendstel", "Zeit (s)", "Zeitstr", "Erfasst am", "Event"]

# -------------------------------------------------
# 🔹 HILFSFUNKTIONEN
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
    """CSV von Google Drive laden und ISO-Datum vereinheitlichen."""
    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh, sep=";")

        for s in spalten:
            if s not in df.columns:
                df[s] = ""

        if "Erfasst am" in df.columns:
            df["Erfasst am"] = df["Erfasst am"].astype(str).replace("nan", "")
            parsed1 = pd.to_datetime(df["Erfasst am"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
            parsed2 = pd.to_datetime(df["Erfasst am"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
            df["Erfasst am_dt"] = parsed1.fillna(parsed2)
            df["Erfasst am"] = df["Erfasst am_dt"].dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
        else:
            df["Erfasst am"] = ""
            df["Erfasst am_dt"] = pd.NaT

        return df
    except Exception as e:
        st.warning(f"⚠️ Datei konnte nicht geladen werden: {e}")
        return pd.DataFrame(columns=spalten)

def speichere_csv(df, file_id):
    """CSV speichern im ISO-Datumsformat. Robust gegen .dt accessor Fehler."""
    try:
        jetzt = datetime.now(MEZ)
        if "Erfasst am_dt" not in df.columns:
            df["Erfasst am_dt"] = jetzt
        else:
            df["Erfasst am_dt"] = pd.to_datetime(df["Erfasst am_dt"], errors="coerce")
            df["Erfasst am_dt"] = df["Erfasst am_dt"].fillna(jetzt)
        df["Erfasst am"] = df["Erfasst am_dt"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S"))

        fh = io.BytesIO()
        df.to_csv(fh, sep=";", index=False)
        fh.seek(0)
        media = MediaIoBaseUpload(fh, mimetype="text/csv", resumable=True)
        drive_service.files().update(fileId=file_id, media_body=media).execute()
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern: {e}")

def lade_fahrer_csv(file_id):
    """Fahrerliste von Google Drive laden."""
    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        df_fahrer = pd.read_csv(fh, sep=";")
        if "Fahrer" not in df_fahrer.columns:
            st.error("🚨 Fahrer.csv muss eine Spalte 'Fahrer' enthalten!")
            return []
        return sorted(df_fahrer["Fahrer"].dropna().unique())
    except Exception as e:
        st.warning(f"⚠️ Fahrer-Datei konnte nicht geladen werden: {e}")
        return []

def get_letzte_drei_indices(df):
    """Ermittelt die drei neuesten Einträge im gesamten Datensatz."""
    df_valid = df.dropna(subset=["Erfasst am_dt"]).sort_values("Erfasst am_dt", ascending=False)
    return set(df_valid.head(3).index)

# -------------------------------------------------
# 🔹 STREAMLIT-APP
# -------------------------------------------------
def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", layout="wide")
    
        # ---- CSS für Zeitboxen ----
    st.markdown("""
    <style>
    .time-box {
        padding: 12px 15px;
        margin-bottom: 8px;
        border-radius: 10px;
        background-color: #1b1b1b; 
        color: white;
        box-shadow: 0px 2px 6px rgba(0,0,0,0.5);
        transition: transform 0.1s ease-in-out, box-shadow 0.1s ease-in-out;
    }
    .time-box:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 12px rgba(0,0,0,0.6);
    }
    .time-box .fahrer-name {
        font-weight: bold;
        font-size: 16px;
    }
    .time-box .zeit {
        font-size: 18px;
        font-weight: bold;
    }
    .time-box .meta {
        font-size: 12px;
        color: gray;
    }
    .time-box.best-event {
    background-color: #00bfff99 !important;  /* Hellblau für Event-Bestzeit */
    color: white;
    font-weight: bold;
    }
    #.time-box.locked {
    #    opacity: 0.6;
    #    background-color: #2a2a2a !important;
    #}
    </style>
    """, unsafe_allow_html=True)
    
    # ---- App-Inhalte (Titel, Event-Auswahl, Eingabe usw.) ----
    st.markdown('<div style="background-color:#c20000;color:white;padding:15px;text-align:center;border-radius:12px;font-size:32px;font-weight:bold;margin-bottom:25px;">🏁 RaceKino Rundenzeiten</div>', unsafe_allow_html=True)

    # ---- Daten laden ----
    df = lade_csv(RUNDENZEITEN_FILE_ID, SPALTEN)
    df_events = lade_csv(EVENTS_FILE_ID, ["Event"])
    events = sorted(df_events["Event"].dropna().unique()) if not df_events.empty else []

    if not events:
        st.warning("Keine Events vorhanden.")
        st.stop()

    # ---- Event-Auswahl ----
    event_filter = st.selectbox("🔹 Wähle ein Event", options=events)

    # ---- Neue Rundenzeit eintragen ----
    st.subheader("🏎️ Neue Rundenzeit eintragen")
    col_fahrer, col_zeit, col_button = st.columns([3,2,1])

    with col_fahrer:
        fahrer_liste = lade_fahrer_csv(FAHRER_FILE_ID)
        if fahrer_liste:
            fahrer = st.selectbox("Fahrer auswählen", options=fahrer_liste)
        else:
            fahrer = None
            st.warning("Keine Fahrer verfügbar!")

    with col_zeit:
        raw_input = st.text_input("6 Ziffern (MSSTTT)", max_chars=6)
        if raw_input:
            clean = "".join(filter(str.isdigit, raw_input))
            formatted = f"{clean[0]}:{clean[1:3]}.{clean[3:6]}" if len(clean)>=6 else ""
            st.markdown(f"🕒 **Eingegebene Zeit:** {formatted}")

    with col_button:
        st.write("")
        if st.button("💾 Hinzufügen", use_container_width=True):
            if not fahrer:
                st.warning("Bitte Fahrer auswählen.")
            elif not raw_input.isdigit() or len(raw_input)!=6:
                st.warning("Bitte genau 6 Ziffern eingeben (MSSMMM).")
            else:
                minuten = int(raw_input[0])
                sekunden = int(raw_input[1:3])
                tausendstel = int(raw_input[3:6])
                if sekunden>59 or tausendstel>999:
                    st.error("Ungültige Zeit.")
                else:
                    zeit_in_sek = zeit_zu_sekunden(minuten, sekunden, tausendstel)
                    jetzt = datetime.now(MEZ)
                    neue_zeile = pd.DataFrame([{
                        "Fahrer": fahrer,
                        "Minuten": minuten,
                        "Sekunden": sekunden,
                        "Tausendstel": tausendstel,
                        "Zeit (s)": zeit_in_sek,
                        "Zeitstr": f"{minuten}:{sekunden:02d}.{tausendstel:03d}",
                        "Erfasst am": jetzt.strftime("%Y-%m-%d %H:%M:%S"),
                        "Erfasst am_dt": jetzt,
                        "Event": event_filter
                    }])
                    df = pd.concat([df, neue_zeile], ignore_index=True)
                    speichere_csv(df, RUNDENZEITEN_FILE_ID)
                    st.success(f"✅ Zeit für {fahrer} unter Event '{event_filter}' gespeichert!")
                    st.rerun()

    # ---- Rangliste ----
    df_event = df[df["Event"]==event_filter]
    if not df_event.empty:
        event_bestzeit = df_event["Zeit (s)"].min()
    else:
        event_bestzeit = None
    if not df_event.empty:
        rangliste = []
        for name, gruppe in df_event.groupby("Fahrer"):
            beste3 = gruppe["Zeit (s)"].nsmallest(3)
            if len(beste3)==3:
                rangliste.append({
                    "Fahrer": name,
                    "Durchschnitt (Top 3)": sekunden_zu_zeitstr(beste3.mean()),
                    "Wert": beste3.mean()
                })
        if rangliste:
            st.subheader(f"🏆 Rangliste für Event: {event_filter}")
            medaillen = ["🥇","🥈","🥉"]
            rang_df = pd.DataFrame(rangliste).sort_values("Wert").reset_index(drop=True)
            rang_df["Platz"] = rang_df.index+1
            rang_df["Medaille"] = rang_df["Platz"].apply(lambda x: medaillen[x-1] if x<=3 else "")

            # CSS für Medaillen-Hintergrund
            st.markdown("""
            <style>
            .gold { background-color: #FFD700CC; color: black; padding: 8px; border-radius: 8px; margin-bottom: 4px; }
            .silver { background-color: #C0C0C0CC; color: black; padding: 8px; border-radius: 8px; margin-bottom: 4px; }
            .bronze { background-color: #CD7F32CC; color: white; padding: 8px; border-radius: 8px; margin-bottom: 4px; }
            .ranking-entry { padding: 8px; margin-bottom: 4px; border-radius: 8px; }
            </style>
            """, unsafe_allow_html=True)

            for _, row in rang_df.iterrows():
                style = (
                    "gold" if row["Platz"]==1 
                    else "silver" if row["Platz"]==2 
                    else "bronze" if row["Platz"]==3 
                    else ""
                )
                st.markdown(
                    f'<div class="ranking-entry {style}">{row["Medaille"]} <b>{row["Platz"]}. {row["Fahrer"]}</b> – {row["Durchschnitt (Top 3)"]}</div>',
                    unsafe_allow_html=True
                )

        else:
            st.info("Mindestens 3 Zeiten pro Fahrer erforderlich.")

    # ---- Letzte Rundenzeiten ----
    st.subheader(f"⏱️ Letzte/Beste Rundenzeiten für Event: {event_filter}")
    fahrer_filter = st.multiselect("Filter nach Fahrer:", options=sorted(df_event["Fahrer"].unique()), default=None)
    sortierung = st.radio("Sortierung:", ["Neueste Einträge zuerst","Schnellste Zeiten zuerst"], horizontal=True)
    df_filtered = df_event[df_event["Fahrer"].isin(fahrer_filter)] if fahrer_filter else df_event
    df_anzeige = df_filtered.sort_values("Erfasst am_dt", ascending=False) if sortierung=="Neueste Einträge zuerst" else df_filtered.sort_values("Zeit (s)")
    df_anzeige = df_anzeige.head(st.slider("Anzahl angezeigter Zeiten", 5, 50, 10))

    letzte_drei_indices = get_letzte_drei_indices(df)

    # ---- Bestzeiten für Hervorhebung ----
    best_dict = {}
    top3_dict = {}
    for name, gruppe in df_event.groupby("Fahrer"):
        sortiert = gruppe.sort_values("Zeit (s)")
        best_dict[name] = sortiert.iloc[0]["Zeit (s)"] if not sortiert.empty else None
        top3_dict[name] = set(sortiert["Zeit (s)"].nsmallest(3))

    for idx, row in df_anzeige.iterrows():
        col1, col2 = st.columns([6,1])

        ist_bestzeit = abs(row["Zeit (s)"] - best_dict.get(row["Fahrer"], float("inf"))) < 0.0001
        ist_top3 = row["Zeit (s)"] in top3_dict.get(row["Fahrer"], set())
        ist_event_best = event_bestzeit is not None and abs(row["Zeit (s)"] - event_bestzeit) < 0.0001

        # Box-Hintergrund für persönliche Bestzeit
        box_style = "background-color:#fff9b1;color:black;" if ist_bestzeit else ""

        # Zusätzliche Klasse, wenn Event-Bestzeit
        extra_class = "best-event" if ist_event_best else ""

        zeit_html = f"⭐ <b>{row['Zeitstr']}</b>" if ist_top3 else row["Zeitstr"]
        best_text = " <b>Persönliche Bestzeit</b>" if ist_bestzeit else ""
        event_text = " <b>Event-Bestzeit</b>" if ist_event_best else ""

        locked_class = "" if row.name in letzte_drei_indices else "locked"

        with col1:
            st.markdown(
                f'<div class="time-box {locked_class} {extra_class}" style="{box_style}">'
                f'<div class="fahrer-name">{row["Fahrer"]}</div>'
                f'<div class="zeit">{zeit_html}</div>'
                f'<div class="meta">Event: {row["Event"]} – Erfasst am: {row["Erfasst am"]}{best_text}{event_text}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col2:
            if row.name in letzte_drei_indices:
                if st.button("🗑️", key=f"del_{row.name}"):
                    df = df.drop(index=row.name).reset_index(drop=True)
                    speichere_csv(df, RUNDENZEITEN_FILE_ID)
                    st.success("✅ Eintrag gelöscht!")
                    st.rerun()
            else:
                st.markdown("<div style='text-align:center;color:gray;font-size:12px;'>🔒 Gesperrt</div>", unsafe_allow_html=True)


    # ---- CSV Download & Alle löschen ----
    col_a, col_b = st.columns(2)

    # CSV Download
    with col_a:
        st.download_button(
            "📥 Alle Zeiten als CSV",
            df_event.to_csv(index=False, sep=";").encode("utf-8"),
            "rundenzeiten.csv",
            "text/csv",
            use_container_width=True
        )

    # Alle löschen mit Passwort
    with col_b:
        # Session-State Initialisierung
        if "show_delete_password" not in st.session_state:
            st.session_state["show_delete_password"] = False

        # Button zum Anzeigen der Passwortabfrage
        if not st.session_state["show_delete_password"]:
            if st.button("🗑️ Alle Zeiten für Event löschen", use_container_width=True):
                st.session_state["show_delete_password"] = True
        else:
            st.warning("⚠️ Bitte Passwort eingeben, um alle Zeiten zu löschen:")
            passwort_eingabe = st.text_input("🔑 Passwort:", type="password")

            col_yes, col_no = st.columns([1,1])
            with col_yes:
                if st.button("🗑️ Ja, löschen", use_container_width=True):
                    if passwort_eingabe == LOESCH_PASSWORT:
                        df = df[df["Event"] != event_filter]
                        speichere_csv(df, RUNDENZEITEN_FILE_ID)
                        st.success("🗑️ Alle Zeiten für Event gelöscht!")
                        st.session_state["show_delete_password"] = False
                        st.rerun()
                    else:
                        st.error("❌ Falsches Passwort. Löschvorgang abgebrochen.")
            with col_no:
                if st.button("❌ Abbrechen", use_container_width=True):
                    st.session_state["show_delete_password"] = False
                    st.info("Löschvorgang abgebrochen.")

# -------------------------------------------------
if __name__=="__main__":
    main()
