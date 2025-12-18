import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime
import uuid

class SuspensionDB:
    """
    Gestisce la connessione con Google Sheets per Piloti, Garage e Sessioni.
    """
    
    @staticmethod
    def get_connection():
        # Crea la connessione usando i secrets di Streamlit
        return st.connection("gsheets", type=GSheetsConnection)

    @staticmethod
    def load_data(sheet_name):
        """Legge un foglio specifico e ritorna un DataFrame pulito"""
        conn = SuspensionDB.get_connection()
        try:
            # Legge tutto il foglio specificato (PILOTI, GARAGE, o DIARIO)
            df = conn.read(worksheet=sheet_name, ttl=0) # ttl=0 per non avere cache vecchia
            return df.dropna(how="all") # Rimuove righe vuote
        except Exception as e:
            st.error(f"Errore lettura DB ({sheet_name}): {e}")
            return pd.DataFrame()

    @staticmethod
    def save_session(id_mezzo, pista, condizione, feedback, rating, dati_tecnici):
        """
        Salva una nuova sessione di lavoro nel foglio DIARIO.
        """
        conn = SuspensionDB.get_connection()
        
        # 1. Carica dati esistenti
        df_diario = SuspensionDB.load_data("DIARIO")
        
        # 2. Crea la nuova riga
        new_row = pd.DataFrame([{
            "id_sessione": str(uuid.uuid4())[:8], # Genera ID corto univoco
            "id_mezzo": id_mezzo,
            "data": datetime.now().strftime("%Y-%m-%d"),
            "pista_luogo": pista,
            "condizione": condizione,
            "feedback_text": feedback,
            "rating": rating,
            "dati_tecnici_json": json.dumps(dati_tecnici) # Converte il dizionario in testo JSON
        }])
        
        # 3. Unisce e Aggiorna
        updated_df = pd.concat([df_diario, new_row], ignore_index=True)
        conn.update(worksheet="DIARIO", data=updated_df)
        return True

    @staticmethod
    def get_piloti_options():
        """Ritorna una lista di piloti formattata per il menu a tendina"""
        df = SuspensionDB.load_data("PILOTI")
        if df.empty: return ["Nessun Pilota Trovato"]
        # Crea stringhe tipo: "Mario Rossi (P001)"
        return [f"{row['nome_completo']} ({row['id_pilota']})" for _, row in df.iterrows()]

    @staticmethod
    def get_mezzi_by_pilota(id_pilota_selezionato):
        """Filtra il garage in base al pilota scelto"""
        df = SuspensionDB.load_data("GARAGE")
        if df.empty: return []
        # Filtra solo le moto di quel pilota
        filtered = df[df['id_pilota'] == id_pilota_selezionato]
        return [f"{row['modello']} - {row['tipo']} ({row['id_mezzo']})" for _, row in filtered.iterrows()]
