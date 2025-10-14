import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time

DATEIPFAD = "rundenzeiten.csv"

# ---------------- Hilfsfunktionen ----------------
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
    return pd.read_csv(DATEIPFAD, sep=";", encoding="utf-8")

def speichere_zeiten(df):
    df.to_csv(DATEIPFAD, sep=";", index=False, encoding="utf-8")

# ---------------- App ----------------
def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", layout="wide")

    # Style (unverändert)
    st.markdown("""
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
    """, unsafe_allow_html=True)

    st.markdown('<div class="title">🏁 RaceKino Rundenzeiten</div>', unsafe_allow_html=True)

    # lade dataframe
    df = lade_zeiten()

    # session defaults
    if "zeit_input_field" not in st.session_state:
        st.session_state["zeit_input_field"] = ""
    if "formatted_time" not in st.session_state:
        st.session_state["formatted_time"] = ""
    if "show_delete_all_confirm" not in st.session_state:
        st.session_state["show_delete_all_confirm"] = False

    # Callback für Live-Formatierung — wird bei jedem Tipp-Event ausgelöst
    def update_time():
        raw = st.session_state.get("zeit_input_field", "")
        clean = "".join(filter(str.isdigit, raw))
        formatted = ""
        if len(clean) >= 1:
            # Minute (1 Ziffer) + colon
            formatted = clean[0] + ":"
            # Sekunden: show partial or full
            if len(clean) == 2:
                formatted += clean[1]
            elif len(clean) >= 3:
                formatted += clean[1:3] + "."
                if len(clean) > 3:
                    formatted += clean[3:6]
        st.session_state["formatted_time"] = formatted

    # Callback für Speichern (on_click) — liest Session-State, schreibt CSV, leert Felder, rerun
    def save_time():
        raw = st.session_state.get("zeit_input_field", "").strip()
        fahrer = st.session_state.get("fahrername", "").strip()
        if not fahrer:
            st.warning("Bitte Fahrername eingeben.")
            return
        if not raw.isdigit() or len(raw) != 6:
            st.warning("Bitte genau 6 Ziffern eingeben (Format M SS MMM).")
            return
        try:
            minuten = int(raw[0])
            sekunden = int(raw[1:3])
            tausendstel = int(raw[3:6])
            if sekunden > 59 or tausendstel > 999:
                st.error("Ungültige Zeit. Sekunden ≤ 59, Tausendstel ≤ 999.")
                return
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
            # lade frische df (Vermeidung von Race-Conditions)
            df_local = lade_zeiten()
            df_local = pd.concat([df_local, neue_zeile], ignore_index=True)
            speichere_zeiten(df_local)
            # leere inputs
            st.session_state["zeit_input_field"] = ""
            st.session_state["formatted_time"] = ""
            st.session_state["fahrername"] = ""
            # Feedback und refresh
            st.success(f"✅ Zeit für {fahrer} gespeichert!")
            time.sleep(0.6)
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Fehler beim Verarbeiten der Eingabe: {e}")

    # ---------------- Eingabefelder (ohne value=, nur key und on_change) ----------------
    st.subheader("🏎️ Neue Rundenzeit eintragen")
    col1, col2 = st.columns([2, 2])
    with col1:
        st.text_input("Fahrername", key="fahrername")  # key-backed input
    with col2:
        # das wichtige: KEIN value=..., nur key=... und on_change=update_time
        st.text_input("6 Ziffern eingeben (Format: M SS MMM)", max_chars=6, key="zeit_input_field", on_change=update_time)

    # Live-Vorschau (wird bei jedem Zeichen aktualisiert durch update_time)
    if st.session_state.get("formatted_time"):
        st.markdown(f"🕒 **Eingegebene Zeit:** {st.session_state['formatted_time']}")
    else:
        st.markdown("<span style='color:#888;'>Bitte Ziffern eingeben (z. B. 125512)</span>", unsafe_allow_html=True)

    # Speichern-Button mit on_click -> save_time (vermeidet setitem-Kollisionen)
    st.button("💾 Hinzufügen", use_container_width=True, on_click=save_time)

    # ---------------- Rangliste ----------------
    df = lade_zeiten()  # reload nach evtl. Änderungen
    if not df.empty:
        rangliste = []
        for name, gruppe in df.groupby("Fahrer"):
            beste3 = gruppe["Zeit (s)"].nsmallest(3)
            if len(beste3) == 3:
                avg = beste3.mean()
                rangliste.append({"Fahrer": name, "Durchschnitt (Top 3)": sekunden_zu_zeitstr(avg), "Wert": avg})
        if rangliste:
            st.subheader("🏆 Aktuelle Rangliste (Top 3 Zeiten)")
            rang_df = pd.DataFrame(rangliste).sort_values("Wert").reset_index(drop=True)
            rang_df["Platz"] = rang_df.index + 1
            for _, row in rang_df.iterrows():
                style = "gold" if row["Platz"] == 1 else "silver" if row["Platz"] == 2 else "bronze" if row["Platz"] == 3 else ""
                st.markdown(f'<div class="ranking-entry {style}"><b>{row["Platz"]}. {row["Fahrer"]}</b> – {row["Durchschnitt (Top 3)"]}</div>', unsafe_allow_html=True)
            csv_rang = rang_df[["Platz", "Fahrer", "Durchschnitt (Top 3)"]].to_csv(index=False, sep=";").encode("utf-8")
            st.download_button("📥 Rangliste als CSV", csv_rang, "rangliste.csv", "text/csv", use_container_width=True)
        else:
            st.info("Mindestens ein Fahrer braucht 3 Zeiten für die Rangliste.")

    # ---------------- Anzeige letzte 10, Filter + Sort ----------------
    if not df.empty:
        st.subheader("⏱️ Letzte 10 Rundenzeiten")

        fahrer_filter = st.multiselect("Filter nach Fahrer:", options=sorted(df["Fahrer"].unique()), default=None)
        sortierung = st.radio("Sortierung:", ["Neueste Einträge zuerst", "Schnellste Zeiten zuerst"], horizontal=True)

        df_filtered = df[df["Fahrer"].isin(fahrer_filter)] if fahrer_filter else df

        if sortierung == "Neueste Einträge zuerst":
            try:
                df_filtered["Erfasst_parsed"] = pd.to_datetime(df_filtered["Erfasst am"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
                df_sorted = df_filtered.sort_values("Erfasst_parsed", ascending=False)
            except Exception:
                df_sorted = df_filtered.sort_values("Erfasst am", ascending=False)
        else:
            df_sorted = df_filtered.sort_values("Zeit (s)", ascending=True)

        df_anzeige = df_sorted.head(10)

        for _, row in df_anzeige.iterrows():
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f'<div class="time-box"><b>{row["Fahrer"]}</b><br>⏱️ {row["Zeitstr"]} <span style="color:gray;font-size:12px;">({row["Erfasst am"]})</span></div>', unsafe_allow_html=True)
            with col2:
                key = f"del_{row.name}"
                if st.button("🗑️", key=key, help="Diesen Eintrag löschen"):
                    # löschen über Originalindex: lade erneut, drop, speichern, rerun
                    df_local = lade_zeiten()
                    if row.name in df_local.index:
                        df_local = df_local.drop(index=row.name).reset_index(drop=True)
                        speichere_zeiten(df_local)
                        st.success("✅ Eintrag gelöscht.")
                        time.sleep(0.8)
                        st.experimental_rerun()
                    else:
                        st.error("Eintrag konnte nicht gefunden werden.")

        # CSV Export + Alle löschen (2-stufig)
        col_a, col_b = st.columns(2)
        with col_a:
            csv_zeiten = df.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button("📥 Alle Zeiten als CSV", csv_zeiten, "rundenzeiten.csv", "text/csv", use_container_width=True)

        with col_b:
            if not st.session_state.get("show_delete_all_confirm", False):
                if st.button("🗑️ Alle Rundenzeiten löschen", use_container_width=True):
                    st.session_state["show_delete_all_confirm"] = True
            else:
                st.warning("⚠️ Willst du wirklich alle Zeiten löschen?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("🗑️ Ja, löschen", key="delete_all_confirm", use_container_width=True):
                        if os.path.exists(DATEIPFAD):
                            os.remove(DATEIPFAD)
                        st.session_state["show_delete_all_confirm"] = False
                        st.success("🗑️ Alle Zeiten gelöscht.")
                        time.sleep(0.8)
                        st.experimental_rerun()
                with col_no:
                    if st.button("❌ Abbrechen", key="cancel_delete_all", use_container_width=True):
                        st.session_state["show_delete_all_confirm"] = False
                        st.info("Löschvorgang abgebrochen.")
    else:
        st.info("Noch keine Rundenzeiten erfasst.")

if __name__ == "__main__":
    main()
