import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json

class SuspensionDB:
    """
    Gestisce la lettura e scrittura su Google Sheets.
    Richiede che il file .streamlit/secrets.toml sia configurato correttamente.
    """

    @staticmethod
    def get_connection():
        """Recupera l'oggetto connessione di Streamlit."""
        return st.connection("gsheets", type=GSheetsConnection)

    @staticmethod
    def load_projects():
        """
        Carica tutti i progetti salvati dal foglio 'Projects'.
        Ritorna un DataFrame Pandas.
        """
        conn = SuspensionDB.get_connection()
        try:
            # ttl="0" forza il refresh dei dati (niente cache) per vedere subito i nuovi salvataggi
            df = conn.read(worksheet="Projects", ttl="0")
            
            # Se il foglio è vuoto o mancano colonne, inizializza la struttura
            required_cols = ["id", "date", "model", "rider_weight", "fork_data", "shock_data", "notes"]
            if df.empty or not all(col in df.columns for col in required_cols):
                return pd.DataFrame(columns=required_cols)
            
            # Ordina per data decrescente (più recenti in alto)
            df = df.sort_values(by="date", ascending=False)
            return df
            
        except Exception as e:
            st.error(f"Errore nel caricamento database: {e}")
            return pd.DataFrame()

    @staticmethod
    def save_project(model, weight, fork_data, shock_data, notes=""):
        """
        Salva una nuova configurazione nel database.
        I dati complessi (fork_data, shock_data) vengono convertiti in JSON string.
        """
        conn = SuspensionDB.get_connection()
        df = SuspensionDB.load_projects()

        # Creazione nuova riga
        new_entry = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"), # ID univoco basato sul tempo
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "model": model,
            "rider_weight": weight,
            # Serializzazione JSON: converte i dict in stringhe per salvarli nel foglio
            "fork_data": json.dumps(fork_data),
            "shock_data": json.dumps(shock_data),
            "notes": notes
        }

        # Aggiungi al DataFrame esistente
        updated_df = pd.concat([pd.DataFrame([new_entry]), df], ignore_index=True)

        try:
            conn.update(worksheet="Projects", data=updated_df)
            st.toast("✅ Progetto salvato con successo!", icon="💾")
        except Exception as e:
            st.error(f"Errore durante il salvataggio: {e}")

    @staticmethod
    def delete_project(project_id):
        """Elimina un progetto tramite ID."""
        conn = SuspensionDB.get_connection()
        df = SuspensionDB.load_projects()
        
        # Filtra via l'ID da cancellare
        updated_df = df[df["id"] != str(project_id)] # Assicura confronto stringa
        
        try:
            conn.update(worksheet="Projects", data=updated_df)
            st.toast("🗑️ Progetto eliminato.", icon="⚠️")
            st.rerun()
        except Exception as e:
            st.error(f"Errore cancellazione: {e}")

    @staticmethod
    def parse_config(json_str):
        """Helper per convertire la stringa JSON del database in Dizionario Python."""
        try:
            return json.loads(json_str)
        except:
            return {}
