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

MEZ = pytz.timezone("Europe/Berlin")

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
    """Lädt CSV-Datei und normalisiert Datum auf ISO-Format (YYYY-MM-DD HH:MM:SS)."""
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

        # Datumsformat vereinheitlichen
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
    """Speichert DataFrame im ISO-Datumsformat."""
    try:
        if "Erfasst am_dt" in df.columns:
            df["Erfasst am"] = df["Erfasst am_dt"].dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
        else:
            df["Erfasst am"] = pd.to_datetime(
                df["Erfasst am"], errors="coerce", dayfirst=True
            ).dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")

        fh = io.BytesIO()
        df.to_csv(fh, sep=";", index=False)
        fh.seek(0)
        media = MediaIoBaseUpload(fh, mimetype="text/csv", resumable=True)
        drive_service.files().update(fileId=file_id, media_body=media).execute()
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern: {e}")

def get_letzte_drei_indices(df):
    """Ermittelt Indizes der drei neuesten Einträge im gesamten Datensatz."""
    df_valid = df.dropna(subset=["Erfasst am_dt"]).sort_values("Erfasst am_dt", ascending=False)
    return set(df_valid.head(3).index)

# -------------------------------------------------
# 🔹 STREAMLIT-APP
# -------------------------------------------------
def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", layout="wide")

    # ---- Design ----
    st.markdown("""
    <style>
    body { background-color: #0e0e0e; color: white; }
    .block-container { max-width: 1100px; margin: auto; }
    .title { background-color: #c20000; color: white; text-align: center; padding: 15px; border-radius: 12px; font-size: 32px; font-weight: bold; margin-bottom: 25px; }
    .ranking-entry { padding: 8px; margin-bottom: 4px; border-radius: 8px; }
    .gold { background-color: #FFD700CC; color: black; }
    .silver { background-color: #C0C0C0CC; color: black; }
    .bronze { background-color: #CD7F32CC; color: white; }
    .time-box { background-color: #1b1b1b; padding: 10px; border-radius: 8px; margin-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="title">🏁 RaceKino Rundenzeiten</div>', unsafe_allow_html=True)

    # ---- Daten laden ----
    df = lade_csv(RUNDENZEITEN_FILE_ID, ["Fahrer", "Minuten", "Sekunden", "Tausendstel", "Zeit (s)", "Zeitstr", "Erfasst am", "Event"])
    df_events = lade_csv(EVENTS_FILE_ID, ["Event"])
    events = sorted(df_events["Event"].dropna().unique()) if not df_events.empty else []

    if not events:
        st.warning("Keine Events vorhanden.")
        st.stop()

    # ---- Event-Auswahl ----
    event_filter = st.selectbox("🔹 Wähle ein Event", options=events)

    # ---- Neue Rundenzeit eintragen ----
    st.subheader("🏎️ Neue Rundenzeit eintragen")
    col_fahrer, col_zeit, col_button = st.columns([3, 2, 1])

    with col_fahrer:
        fahrer = st.text_input("Fahrername")

    with col_zeit:
        raw_input = st.text_input("6 Ziffern (MSSTTT)", max_chars=6)
        if raw_input:
            clean = "".join(filter(str.isdigit, raw_input))
            formatted = f"{clean[0]}:{clean[1:3]}.{clean[3:6]}" if len(clean) >= 6 else ""
            st.markdown(f"🕒 **Eingegebene Zeit:** {formatted}")

    with col_button:
        st.write("")
        if st.button("💾 Hinzufügen", use_container_width=True):
            if not fahrer:
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
                    jetzt = datetime.now(MEZ)
                    zeitstr = f"{minuten}:{sekunden:02d}.{tausendstel:03d}"

                    neue_zeile = pd.DataFrame([{
                        "Fahrer": fahrer,
                        "Minuten": minuten,
                        "Sekunden": sekunden,
                        "Tausendstel": tausendstel,
                        "Zeit (s)": zeit_in_sek,
                        "Zeitstr": zeitstr,
                        "Erfasst am": jetzt.strftime("%Y-%m-%d %H:%M:%S"),
                        "Erfasst am_dt": jetzt,
                        "Event": event_filter
                    }])

                    df = pd.concat([df, neue_zeile], ignore_index=True)
                    speichere_csv(df, RUNDENZEITEN_FILE_ID)
                    st.success(f"✅ Zeit für {fahrer} unter Event '{event_filter}' gespeichert!")
                    st.rerun()

    # ---- Rangliste ----
    df_event = df[df["Event"] == event_filter]
    if not df_event.empty:
        rangliste = []
        for name, gruppe in df_event.groupby("Fahrer"):
            beste3 = gruppe["Zeit (s)"].nsmallest(3)
            if len(beste3) == 3:
                rangliste.append({
                    "Fahrer": name,
                    "Durchschnitt (Top 3)": sekunden_zu_zeitstr(beste3.mean()),
                    "Wert": beste3.mean()
                })

        if rangliste:
            st.subheader(f"🏆 Rangliste für Event: {event_filter}")
            medaillen = ["🥇", "🥈", "🥉"]
            rang_df = pd.DataFrame(rangliste).sort_values("Wert").reset_index(drop=True)
            rang_df["Platz"] = rang_df.index + 1
            rang_df["Medaille"] = rang_df["Platz"].apply(lambda x: medaillen[x - 1] if x <= 3 else "")

            for _, row in rang_df.iterrows():
                style = (
                    "gold" if row["Platz"] == 1
                    else "silver" if row["Platz"] == 2
                    else "bronze" if row["Platz"] == 3
                    else ""
                )
                st.markdown(
                    f'<div class="ranking-entry {style}">'
                    f'{row["Medaille"]} <b>{row["Platz"]}. {row["Fahrer"]}</b> – '
                    f'{row["Durchschnitt (Top 3)"]}'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("Mindestens 3 Zeiten pro Fahrer erforderlich.")

    # ---- Letzte Rundenzeiten ----
    st.subheader(f"⏱️ Letzte/Beste Rundenzeiten für Event: {event_filter}")
    df_event = df[df["Event"] == event_filter]

    fahrer_filter = st.multiselect("Filter nach Fahrer:", options=sorted(df_event["Fahrer"].unique()), default=None)
    sortierung = st.radio("Sortierung:", ["Neueste Einträge zuerst", "Schnellste Zeiten zuerst"], horizontal=True)

    df_filtered = df_event[df_event["Fahrer"].isin(fahrer_filter)] if fahrer_filter else df_event
    df_anzeige = df_filtered.sort_values("Erfasst am_dt", ascending=False) if sortierung == "Neueste Einträge zuerst" else df_filtered.sort_values("Zeit (s)")
    df_anzeige = df_anzeige.head(st.slider("Anzahl angezeigter Zeiten", 5, 50, 10))

    letzte_drei_indices = get_letzte_drei_indices(df)

    # ---- Anzeige mit Löschbeschränkung ----
    for idx, row in df_anzeige.iterrows():
        col1, col2 = st.columns([6, 1])
        ist_bestzeit = abs(row["Zeit (s)"] - df_event[df_event["Fahrer"] == row["Fahrer"]]["Zeit (s)"].min()) < 0.0001
        box_style = "background-color: #fff9b1; color: black;" if ist_bestzeit else ""

        with col1:
            st.markdown(
                f'<div class="time-box" style="{box_style}">'
                f'<b>{row["Fahrer"]}</b> – <i>{row["Event"]}</i><br>'
                f'⏱️ {row["Zeitstr"]}<br>'
                f'<span style="color:gray;font-size:12px;">({row["Erfasst am"]})</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col2:
            if row.name in letzte_drei_indices:
                if st.button("🗑️", key=f"del_{row.name}"):
                    df = df.drop(index=row.name)
                    df.reset_index(drop=True, inplace=True)
                    speichere_csv(df, RUNDENZEITEN_FILE_ID)
                    st.success("✅ Eintrag gelöscht!")
                    st.rerun()
            else:
                st.markdown("<div style='text-align:center;color:gray;font-size:12px;'>🔒 Gesperrt</div>", unsafe_allow_html=True)

    # ---- Download & Alle löschen ----
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "📥 Alle Zeiten als CSV",
            df_event.to_csv(index=False, sep=";").encode("utf-8"),
            "rundenzeiten.csv",
            "text/csv",
            use_container_width=True,
            key="download_csv_button"
        )

    with col_b:
        if st.button("🗑️ Alle Zeiten für Event löschen", use_container_width=True):
            df = df[df["Event"] != event_filter]
            speichere_csv(df, RUNDENZEITEN_FILE_ID)
            st.success("🗑️ Alle Zeiten gelöscht!")
            st.rerun()

# -------------------------------------------------
if __name__ == "__main__":
    main()
