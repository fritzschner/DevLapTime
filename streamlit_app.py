import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import os

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
    .gold { background-color: #FFD700AA; color: #2b2b2b; font-weight:bold; }
    .silver { background-color: #C0C0C0AA; color: #2b2b2b; font-weight:bold; }
    .bronze { background-color: #CD7F3233; color: white; font-weight:bold; }
    .time-box { background-color: #1b1b1b; padding: 10px; border-radius: 8px; margin-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="title">🏁 RaceKino Rundenzeiten</div>', unsafe_allow_html=True)

    df = lade_zeiten()

    # ---------------- Event-Filter (oben) ----------------
    vorhandene_events = sorted(df["Event"].unique()) if not df.empty else []
    ausgewähltes_event = st.selectbox("📌 Wähle ein Event aus (Zeiten können nur für ein Event eingegeben werden)", options=vorhandene_events, index=0 if vorhandene_events else None)
    
    st.write("---")

    # ---------------- Eingabeformular ----------------
    st.subheader("🏎️ Neue Rundenzeit eintragen")

    if "zeit_input_temp" not in st.session_state:
        st.session_state["zeit_input_temp"] = ""

    if ausgewähltes_event:
        col1, col2 = st.columns([2, 2])
        fahrer = col1.text_input("Fahrername", key="fahrername")
        raw_input = col2.text_input(
            "6 Ziffern eingeben (Format: MSSTTT)",
            value=st.session_state["zeit_input_temp"],
            max_chars=6,
            key="zeit_input_field"
        )

        # Live-Formatierung
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

        # Speichern
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
                        jetzt = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y %H:%M:%S")
                        zeitstr = f"{minuten}:{sekunden:02d}.{tausendstel:03d}"
                        neue_zeile = pd.DataFrame([{
                            "Fahrer": fahrer,
                            "Minuten": minuten,
                            "Sekunden": sekunden,
                            "Tausendstel": tausendstel,
                            "Zeit (s)": zeit_in_sek,
                            "Zeitstr": zeitstr,
                            "Erfasst am": jetzt,
                            "Event": ausgewähltes_event
                        }])
                        df = pd.concat([df, neue_zeile], ignore_index=True)
                        speichere_zeiten(df)
                        st.session_state["zeit_input_temp"] = ""
                        st.success(f"✅ Zeit für {fahrer} im Event '{ausgewähltes_event}' gespeichert!")
                except Exception as e:
                    st.error(f"Fehler beim Verarbeiten der Eingabe: {e}")
    else:
        st.info("Bitte wähle ein Event aus, um Zeiten einzugeben.")

    # ---------------- Rangliste ----------------
    if not df.empty:
        rangliste = []
        for name, gruppe in df[df["Event"]==ausgewähltes_event].groupby("Fahrer"):
            beste3 = gruppe["Zeit (s)"].nsmallest(3)
            if len(beste3) == 3:
                avg = beste3.mean()
                rangliste.append({
                    "Fahrer": name,
                    "Durchschnitt (Top 3)": sekunden_zu_zeitstr(avg),
                    "Wert": avg
                })
        if rangliste:
            st.subheader(f"🏆 Aktuelle Rangliste (Top 3 Zeiten) – {ausgewähltes_event}")
            rang_df = pd.DataFrame(rangliste).sort_values("Wert").reset_index(drop=True)
            rang_df["Platz"] = rang_df.index + 1
            for _, row in rang_df.iterrows():
                style = "gold" if row["Platz"] == 1 else "silver" if row["Platz"] == 2 else "bronze" if row["Platz"] == 3 else ""
                st.markdown(
                    f'<div class="ranking-entry {style}">'
                    f'<b>{row["Platz"]}. {row["Fahrer"]}</b> – {row["Durchschnitt (Top 3)"]}'
                    f'</div>', unsafe_allow_html=True
                )

    # ---------------- Letzte 10 Rundenzeiten ----------------
    if not df.empty:
        st.subheader(f"⏱️ Letzte 10 Rundenzeiten – {ausgewähltes_event}")

        fahrer_filter = st.multiselect("Filter nach Fahrer:", options=sorted(df["Fahrer"].unique()), default=None)

        sortierung = st.radio("Sortierung:", ["Neueste Einträge zuerst", "Schnellste Zeiten zuerst"], horizontal=True)
        
        df_filtered = df[df["Event"]==ausgewähltes_event]
        if fahrer_filter:
            df_filtered = df_filtered[df_filtered["Fahrer"].isin(fahrer_filter)]

        df_anzeige = df_filtered.sort_values("Erfasst am", ascending=False) if sortierung=="Neueste Einträge zuerst" else df_filtered.sort_values("Zeit (s)", ascending=True)
        df_anzeige = df_anzeige.head(10)

        for idx, row in df_anzeige.iterrows():
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(
                    f'<div class="time-box">'
                    f'<b>{row["Fahrer"]}</b><br>'
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
            csv_zeiten = df[df["Event"]==ausgewähltes_event].to_csv(index=False, sep=";").encode("utf-8")
            st.download_button("📥 Zeiten als CSV", csv_zeiten, f"{ausgewähltes_event}_zeiten.csv", "text/csv", use_container_width=True)

    # ---------------- Neues Event hinzufügen (unten) ----------------
    st.write("---")
    st.subheader("➕ Neues Event anlegen")
    neues_event = st.text_input("Neues Event hinzufügen", key="neues_event_field")
    if st.button("Event hinzufügen", use_container_width=True):
        if neues_event:
            if neues_event not in vorhandene_events:
                df_empty = lade_zeiten()  # nur um sicherzustellen, dass Datei existiert
                speichere_zeiten(df_empty)  # speichert die Datei falls nicht existent
                st.success(f"✅ Neues Event '{neues_event}' hinzugefügt! Bitte App neu laden, um es auszuwählen.")
            else:
                st.warning("Dieses Event existiert bereits.")
        else:
            st.warning("Bitte einen Eventnamen eingeben.")

# ------------------- Start -------------------
if __name__ == "__main__":
    main()
