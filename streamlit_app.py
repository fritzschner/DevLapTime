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
    """Lädt eine CSV-Datei von Google Drive und stellt sicher, dass alle Spalten vorhanden sind."""
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
        return df
    except Exception as e:
        st.warning(f"⚠️ Datei konnte nicht geladen werden: {e}")
        return pd.DataFrame(columns=spalten)

def speichere_csv(df, file_id):
    """Speichert ein DataFrame als CSV auf Google Drive."""
    try:
        fh = io.BytesIO()
        df.to_csv(fh, sep=";", index=False)
        fh.seek(0)
        media = MediaIoBaseUpload(fh, mimetype="text/csv", resumable=True)
        drive_service.files().update(fileId=file_id, media_body=media).execute()
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern: {e}")

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
    fahrer = st.text_input("Fahrername")
    raw_input = st.text_input("6 Ziffern eingeben (Format: MSSTTT)", max_chars=6)

    if raw_input:
        clean = "".join(filter(str.isdigit, raw_input))
        formatted = f"{clean[0]}:{clean[1:3]}.{clean[3:6]}" if len(clean) >= 6 else ""
        st.markdown(f"🕒 **Eingegebene Zeit:** {formatted}")

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
                jetzt = datetime.now(MEZ).strftime("%d.%m.%Y %H:%M:%S")
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
    if not df.empty and event_filter:
        st.subheader(f"⏱️ Letzte/Beste Rundenzeiten für Event: {event_filter}")
        df_event = df[df["Event"] == event_filter]
        theme_base = st.get_option("theme.base")
        timebox_bg = "#f0f0f0" if theme_base == "light" else "#1b1b1b"
        timebox_color = "black" if theme_base == "light" else "white"

        st.markdown(f"""
        <style>
        .time-box {{
            background-color: {timebox_bg};
            color: {timebox_color};
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
        }}
        </style>
        """, unsafe_allow_html=True)

        fahrer_filter = st.multiselect("Filter nach Fahrer:", options=sorted(df_event["Fahrer"].unique()), default=None)
        sortierung = st.radio("Sortierung:", ["Neueste Einträge zuerst", "Schnellste Zeiten zuerst"], horizontal=True)
        df_filtered = df_event[df_event["Fahrer"].isin(fahrer_filter)] if fahrer_filter else df_event
        df_anzeige = df_filtered.sort_values("Erfasst am", ascending=False) if sortierung == "Neueste Einträge zuerst" else df_filtered.sort_values("Zeit (s)")
        df_anzeige = df_anzeige.head(st.slider("Anzahl angezeigter Zeiten", 5, 50, 10))

    # ---- Bestzeiten ermitteln ----
    top3_dict = {}
    best_dict = {}
    for name, gruppe in df_event.groupby("Fahrer"):
        sortiert = gruppe.sort_values("Zeit (s)")
        best_dict[name] = sortiert.iloc[0]["Zeit (s)"] if not sortiert.empty else None
        top3_dict[name] = set(sortiert["Zeit (s)"].nsmallest(3))

    for idx, row in df_anzeige.iterrows():
        col1, col2 = st.columns([6, 1])
        ist_bestzeit = abs(row["Zeit (s)"] - best_dict.get(row["Fahrer"], float("inf"))) < 0.0001
        ist_top3 = row["Zeit (s)"] in top3_dict.get(row["Fahrer"], set())
        box_style = "background-color: #fff9b1; color: black;" if ist_bestzeit else ""
        best_text = " <b>(Persönliche Bestzeit)</b>" if ist_bestzeit else ""
        zeit_html = f"⭐ <b>{row['Zeitstr']}</b>" if ist_top3 else row["Zeitstr"]

        with col1:
            st.markdown(
                f'<div class="time-box" style="{box_style}">'
                f'<b>{row["Fahrer"]}</b> – <i>{row["Event"]}</i><br>'
                f'⏱️ {zeit_html}{best_text} '
                f'<span style="color:gray;font-size:12px;">({row["Erfasst am"]})</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col2:
            if st.button("🗑️", key=f"del_{row.name}", help="Diesen Eintrag löschen"):
                df = df.drop(row.name).reset_index(drop=True)
                speichere_csv(df, RUNDENZEITEN_FILE_ID)
                st.success("✅ Eintrag gelöscht!")

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
                    speichere_csv(df, RUNDENZEITEN_FILE_ID)
                    st.session_state["show_delete_all_confirm"] = False
                    st.success("🗑️ Alle Zeiten für Event gelöscht.")
                    st.experimental_rerun()
            with col_no:
                if st.button("❌ Abbrechen", key="cancel_delete_all", use_container_width=True):
                    st.session_state["show_delete_all_confirm"] = False
                    st.info("Löschvorgang abgebrochen.")

# -------------------------------------------------
if __name__ == "__main__":
    main()
