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
        return pd.DataFrame(columns=["Fahrer", "Event", "Minuten", "Sekunden", "Tausendstel", "Zeit (s)", "Zeitstr", "Erfasst am"])
    return pd.read_csv(DATEIPFAD, sep=";")

def speichere_zeiten(df):
    df.to_csv(DATEIPFAD, sep=";", index=False)

# ------------------- Hauptfunktion -------------------
def main():
    st.set_page_config(page_title="RaceKino Rundenzeiten", layout="wide")

    # ---------------- Design ----------------
    st.markdown(
        """
        <style>
        body { background-color: #0e0e0e; color: white; }
        .block-container { max-width: 1100px; margin: auto; }
        .title {
            background-color: #c20000; color: white; text-align: center;
            padding: 15px; border-radius: 12px; font-size: 32px; font-weight: bold; margin-bottom: 25px;
        }
        .ranking-entry { padding: 8px; margin-bottom: 4px; border-radius: 8px; }
        .gold { background-color: #FFD70033; }
        .silver { background-color: #C0C0C033; }
        .bronze { background-color: #CD7F3233; }
        .time-box { background-color: #1b1b1b; padding: 10px; border-radius: 8px; margin-bottom: 8px; }
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown('<div class="title">🏁 RaceKino Rundenzeiten</div>', unsafe_allow_html=True)

    df = lade_zeiten()

    # ---------------- Eingabeformular ----------------
    st.subheader("🏎️ Neue Rundenzeit eintragen")

    col1, col2, col3 = st.columns([2,2,2])

    # Fahrername mit Autovervollständigung
    fahrer_optionen = sorted(df["Fahrer"].unique()) if not df.empty else []
    fahrer = col1.selectbox("Fahrername", options=fahrer_optionen + [""], index=len(fahrer_optionen), key="fahrername_input")
    fahrer_neu = col1.text_input("Neuer Fahrer (falls nicht vorhanden)", key="fahrer_neu")
    if fahrer_neu:
        fahrer = fahrer_neu

    # Eventname mit Autovervollständigung
    event_optionen = sorted(df["Event"].unique()) if not df.empty else []
    event = col2.selectbox("Event", options=event_optionen + [""], index=len(event_optionen), key="event_input")
    event_neu = col2.text_input("Neues Event (falls nicht vorhanden)", key="event_neu")
    if event_neu:
        event = event_neu

    # Eingabe der Zeit
    raw_input = col3.text_input(
        "6 Ziffern eingeben (Format: MSSTTT)",
        value=st.session_state.get("zeit_input_field",""),
        max_chars=6,
        key="zeit_input"
    )

    # Live-Formatierung
    formatted_input = ""
    if raw_input:
        clean = "".join(filter(str.isdigit, raw_input))
        if len(clean) >= 1:
            formatted_input += clean[0] + ":"
        if len(clean) >= 3:
            formatted_input += clean[1:3] + "."
        if len(clean) > 3:
            formatted_input += clean[3:6]
        st.markdown(f"🕒 **Eingegebene Zeit:** {formatted_input}")

    # Speichern-Button
    if st.button("💾 Hinzufügen", use_container_width=True):
        if not fahrer or not event:
            st.warning("Bitte Fahrer und Event angeben.")
        elif not raw_input.isdigit() or len(raw_input)!=6:
            st.warning("Bitte genau 6 Ziffern eingeben (Format M SS MMM).")
        else:
            try:
                minuten = int(raw_input[0])
                sekunden = int(raw_input[1:3])
                tausendstel = int(raw_input[3:6])
                if sekunden>59 or tausendstel>999:
                    st.error("Ungültige Zeit. Sekunden ≤59, Tausendstel ≤999.")
                else:
                    zeit_in_sek = zeit_zu_sekunden(minuten, sekunden, tausendstel)
                    jetzt = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                    zeitstr = f"{minuten}:{sekunden:02d}.{tausendstel:03d}"
                    neue_zeile = pd.DataFrame([{
                        "Fahrer": fahrer,
                        "Event": event,
                        "Minuten": minuten,
                        "Sekunden": sekunden,
                        "Tausendstel": tausendstel,
                        "Zeit (s)": zeit_in_sek,
                        "Zeitstr": zeitstr,
                        "Erfasst am": jetzt
                    }])
                    df = pd.concat([df, neue_zeile], ignore_index=True)
                    speichere_zeiten(df)
                    st.session_state["zeit_input_field"] = ""
                    st.success(f"✅ Zeit für {fahrer} im Event '{event}' gespeichert!")
            except Exception as e:
                st.error(f"Fehler beim Verarbeiten der Eingabe: {e}")

    # ---------------- Event Filter ----------------
    st.subheader("⏱️ Letzte 10 Rundenzeiten")
    event_filter = st.selectbox("Event auswählen:", options=["Alle"] + (sorted(df["Event"].unique()) if not df.empty else []))
    fahrer_filter = st.multiselect("Filter nach Fahrer:", options=sorted(df["Fahrer"].unique()) if not df.empty else [], default=None)
    sortierung = st.radio("Sortierung:", ["Neueste Einträge zuerst","Schnellste Zeiten zuerst"], horizontal=True)

    df_filtered = df.copy()
    if event_filter != "Alle":
        df_filtered = df_filtered[df_filtered["Event"]==event_filter]
    if fahrer_filter:
        df_filtered = df_filtered[df_filtered["Fahrer"].isin(fahrer_filter)]

    df_anzeige = df_filtered.sort_values("Erfasst am", ascending=False) if sortierung=="Neueste Einträge zuerst" else df_filtered.sort_values("Zeit (s)", ascending=True)
    df_anzeige = df_anzeige.head(10)

    for idx, row in df_anzeige.iterrows():
        col1, col2 = st.columns([6,1])
        with col1:
            st.markdown(
                f'<div class="time-box"><b>{row["Fahrer"]}</b> ({row["Event"]})<br>⏱️ {row["Zeitstr"]} <span style="color:gray;font-size:12px;">({row["Erfasst am"]})</span></div>',
                unsafe_allow_html=True
            )
        with col2:
            if st.button("🗑️", key=f"del_{row.name}"):
                df = df.drop(row.name).reset_index(drop=True)
                speichere_zeiten(df)
                st.success("✅ Eintrag gelöscht!")

    # ---------------- Rangliste je Event ----------------
    if not df_filtered.empty:
        st.subheader("🏆 Rangliste (Top 3 je Fahrer) - Event: "+("Alle" if event_filter=="Alle" else event_filter))
        rangliste=[]
        for name, gruppe in df_filtered.groupby("Fahrer"):
            beste3 = gruppe["Zeit (s)"].nsmallest(3)
            if len(beste3)==3:
                avg = beste3.mean()
                rangliste.append({"Fahrer":name,"Durchschnitt (Top 3)":sekunden_zu_zeitstr(avg),"Wert":avg})
        if rangliste:
            rang_df=pd.DataFrame(rangliste).sort_values("Wert").reset_index(drop=True)
            rang_df["Platz"]=rang_df.index+1
            for _, row in rang_df.iterrows():
                style="gold" if row["Platz"]==1 else "silver" if row["Platz"]==2 else "bronze" if row["Platz"]==3 else ""
                st.markdown(f'<div class="ranking-entry {style}"><b>{row["Platz"]}. {row["Fahrer"]}</b> – {row["Durchschnitt (Top 3)"]}</div>',unsafe_allow_html=True)
            csv_rang=rang_df[["Platz","Fahrer","Durchschnitt (Top 3)"]].to_csv(index=False,sep=";").encode("utf-8")
            st.download_button("📥 Rangliste als CSV", csv_rang,"rangliste.csv","text/csv",use_container_width=True)
        else:
            st.info("Mindestens ein Fahrer braucht 3 Zeiten für die Rangliste.")

    # ---------------- CSV Export / Alle löschen ----------------
    col_a,col_b=st.columns(2)
    with col_a:
        csv_zeiten = df.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button("📥 Alle Zeiten als CSV", csv_zeiten,"rundenzeiten.csv","text/csv",use_container_width=True)
    with col_b:
        if st.session_state.get("show_delete_all_confirm") is None:
            st.session_state["show_delete_all_confirm"]=False
        if not st.session_state["show_delete_all_confirm"]:
            if st.button("🗑️ Alle Rundenzeiten löschen",use_container_width=True):
                st.session_state["show_delete_all_confirm"]=True
        else:
            st.warning("⚠️ Willst du wirklich alle Zeiten löschen?")
            col_yes,col_no=st.columns(2)
            with col_yes:
                if st.button("🗑️ Ja, löschen",key="delete_all_confirm",use_container_width=True):
                    if os.path.exists(DATEIPFAD):
                        os.remove(DATEIPFAD)
                    st.session_state["show_delete_all_confirm"]=False
                    st.success("🗑️ Alle Zeiten gelöscht.")
            with col_no:
                if st.button("❌ Abbrechen",key="cancel_delete_all",use_container_width=True):
                    st.session_state["show_delete_all_confirm"]=False
                    st.info("Löschvorgang abgebrochen.")

# ------------------- Start -------------------
if __name__=="__main__":
    main()
