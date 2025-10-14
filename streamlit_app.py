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
    df = pd.read_csv(DATEIPFAD, sep=";", encoding="utf-8")
    return df

def speichere_zeiten(df):
    df.to_csv(DATEIPFAD, sep=";", index=False, encoding="utf-8")

# ------------------- App -------------------
def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", layout="wide")
    # CSS / Theme (beibehalten)
    st.markdown(
        """
        <style>
        body { background-color: #0e0e0e; color: white; }
        .block-container { max-width: 1100px; margin: auto; }
        .title { background-color: #c20000; color: white; text-align: center; padding: 15px; border-radius: 12px; font-size: 32px; font-weight: bold; margin-bottom: 25px; }
        .ranking-entry { padding: 8px; margin-bottom: 4px; border-radius: 8px; }
        .gold { background-color: #FFD70033; }
        .silver { background-color: #C0C0C033; }
        .bronze { background-color: #CD7F3233; }
        .time-box { background-color: #1b1b1b; padding: 10px; border-radius: 8px; margin-bottom: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="title">🏁 RaceKino Rundenzeiten</div>', unsafe_allow_html=True)

    # Lade Daten
    df = lade_zeiten()

    # Session state defaults (für Input-Steuerung / Delete confirm)
    if "show_delete_all_confirm" not in st.session_state:
        st.session_state["show_delete_all_confirm"] = False
    # Keys für die tatsächlichen Text-Inputs (verwende diese Keys, damit wir sie gezielt leeren können)
    if "zeit_input_field" not in st.session_state:
        st.session_state["zeit_input_field"] = ""
    if "fahrer_input_field" not in st.session_state:
        st.session_state["fahrer_input_field"] = ""

    # ---------------- Eingabeformular ----------------
    with st.form("eingabe_formular"):
        col1, col2 = st.columns([2, 2])
        # Fahrername - kontrolliertes Feld
        fahrer = col1.text_input("Fahrername", value=st.session_state["fahrer_input_field"], key="fahrer_input_field")
        # Zeit-Eingabe - kontrolliertes Feld (nur Ziffern)
        raw = col2.text_input("6 Ziffern eingeben (Format: M SS MMM)", value=st.session_state["zeit_input_field"], max_chars=6, key="zeit_input_field")

        # Synchronisiere session_state (wichtig für das Leeren weiter unten)
        st.session_state["zeit_input_field"] = raw
        st.session_state["fahrer_input_field"] = fahrer

        # Live-formatierung (sichtbar schon beim Tippen)
        formatted = ""
        if raw and raw.isdigit():
            # Minute (erste Ziffer) + :
            if len(raw) >= 1:
                formatted = raw[0] + ":"
            # Sekunden (bis 2 Ziffern)
            if len(raw) == 2:
                formatted += raw[1]
            elif len(raw) >= 3:
                formatted = raw[0] + ":" + raw[1:3] + "."
                if len(raw) > 3:
                    formatted += raw[3:6]
            st.markdown(f"🕒 **Eingegebene Zeit:** {formatted}")
        elif raw:
            st.markdown("<span style='color:#888;'>Bitte nur Ziffern eingeben (max. 6), z. B. 125512</span>", unsafe_allow_html=True)

        abgeschickt = st.form_submit_button("💾 Hinzufügen", use_container_width=True)

        if abgeschickt:
            # Re-read latest values from session state to be safe
            raw_val = st.session_state.get("zeit_input_field", "")
            fahrer_val = st.session_state.get("fahrer_input_field", "").strip()

            if not fahrer_val:
                st.warning("Bitte Fahrername eingeben.")
            elif not raw_val.isdigit() or len(raw_val) != 6:
                st.warning("Bitte genau 6 Ziffern eingeben (Format M SS MMM).")
            else:
                try:
                    minuten = int(raw_val[0])
                    sekunden = int(raw_val[1:3])
                    tausendstel = int(raw_val[3:6])
                    if sekunden > 59 or tausendstel > 999:
                        st.error("Ungültige Zeit. Sekunden ≤ 59, Tausendstel ≤ 999.")
                    else:
                        zeit_in_sek = zeit_zu_sekunden(minuten, sekunden, tausendstel)
                        jetzt = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                        zeitstr = f"{minuten}:{sekunden:02d}.{tausendstel:03d}"
                        neue_zeile = pd.DataFrame([{
                            "Fahrer": fahrer_val,
                            "Minuten": minuten,
                            "Sekunden": sekunden,
                            "Tausendstel": tausendstel,
                            "Zeit (s)": zeit_in_sek,
                            "Zeitstr": zeitstr,
                            "Erfasst am": jetzt
                        }])
                        # An df anhängen und speichern
                        df = pd.concat([df, neue_zeile], ignore_index=True)
                        speichere_zeiten(df)

                        # Eingabefelder automatisch leeren über session_state (kein Query-Param Refresh!)
                        st.session_state["zeit_input_field"] = ""
                        st.session_state["fahrer_input_field"] = ""

                        st.success("✅ Zeit hinzugefügt.")
                        time.sleep(0.4)
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
                style = "gold" if row["Platz"] == 1 else "silver" if row["Platz"] == 2 else "bronze" if row["Platz"] == 3 else ""
                st.markdown(
                    f'<div class="ranking-entry {style}"><b>{row["Platz"]}. {row["Fahrer"]}</b> – {row["Durchschnitt (Top 3)"]}</div>',
                    unsafe_allow_html=True
                )
            csv_rang = rang_df[["Platz", "Fahrer", "Durchschnitt (Top 3)"]].to_csv(index=False, sep=";").encode("utf-8")
            st.download_button("📥 Rangliste als CSV", csv_rang, "rangliste.csv", "text/csv", use_container_width=True)
        else:
            st.info("Mindestens ein Fahrer braucht 3 Zeiten für die Rangliste.")

    # ---------------- Filter + Sort + Anzeige letzte 10 ----------------
    if not df.empty:
        st.subheader("⏱️ Letzte 10 Rundenzeiten")

        # Filter: multiselect (zeigt alle Fahrer)
        fahrer_filter = st.multiselect("Filter nach Fahrer:", options=sorted(df["Fahrer"].unique()), default=None)

        # Sort option
        sortierung = st.radio("Sortierung:", ["Neueste Einträge zuerst", "Schnellste Zeiten zuerst"], horizontal=True)

        # Filter anwenden (behalte Originalindex, wichtig für korrektes Löschen)
        if fahrer_filter:
            df_filtered = df[df["Fahrer"].isin(fahrer_filter)]
        else:
            df_filtered = df

        # Sortierung — bei Erfasst am als Datum sortieren (robuster)
        if sortierung == "Neueste Einträge zuerst":
            try:
                df_filtered["Erfasst_parsed"] = pd.to_datetime(df_filtered["Erfasst am"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
                df_sorted = df_filtered.sort_values("Erfasst_parsed", ascending=False)
            except Exception:
                df_sorted = df_filtered.sort_values("Erfasst am", ascending=False)
        else:
            df_sorted = df_filtered.sort_values("Zeit (s)", ascending=True)

        # Show only top 10 of the sorted result; keep original indices so row.name corresponds to CSV row
        df_anzeige = df_sorted.head(10)

        for _, row in df_anzeige.iterrows():
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(
                    f'<div class="time-box"><b>{row["Fahrer"]}</b><br>⏱️ {row["Zeitstr"]} <span style="color:gray;font-size:12px;">({row["Erfasst am"]})</span></div>',
                    unsafe_allow_html=True,
                )
            with col2:
                key = f"del_{row.name}"
                if st.button("🗑️", key=key, help="Diesen Eintrag löschen"):
                    # delete by original index
                    if row.name in df.index:
                        df = df.drop(index=row.name).reset_index(drop=True)
                        speichere_zeiten(df)
                        st.success("✅ Eintrag gelöscht.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Eintrag konnte nicht gefunden werden.")

        # CSV-Export + Alle löschen (2-stufig)
        col_a, col_b = st.columns(2)
        with col_a:
            csv_zeiten = df.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button("📥 Alle Zeiten als CSV", csv_zeiten, "rundenzeiten.csv", "text/csv", use_container_width=True)

        with col_b:
            # Stufe 1: initialer Button
            if not st.session_state["show_delete_all_confirm"]:
                if st.button("🗑️ Alle Rundenzeiten löschen", use_container_width=True):
                    st.session_state["show_delete_all_confirm"] = True
            else:
                st.markdown("⚠️ Willst du wirklich alle Zeiten löschen?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("🗑️ Ja, löschen", key="delete_all_confirm", use_container_width=True):
                        if os.path.exists(DATEIPFAD):
                            os.remove(DATEIPFAD)
                        st.session_state["show_delete_all_confirm"] = False
                        st.error("🗑️ Alle Zeiten gelöscht.")
                        time.sleep(1)
                        st.rerun()
                with col_no:
                    if st.button("❌ Abbrechen", key="cancel_delete_all", use_container_width=True):
                        st.session_state["show_delete_all_confirm"] = False
                        st.info("Löschvorgang abgebrochen.")
    else:
        st.info("Noch keine Rundenzeiten erfasst.")

if __name__ == "__main__":
    main()
