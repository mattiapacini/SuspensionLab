import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

class SuspensionDB:
    @staticmethod
    def get_connection():
        return st.connection("gsheets", type=GSheetsConnection)

    @staticmethod
    def init_db():
        """Inizializza il DB se vuoto o colonne mancanti"""
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Piloti", usecols=list(range(6)), ttl=0)
            if df.empty:
                df = pd.DataFrame(columns=["ID", "Nome", "Peso", "Livello", "Moto", "Note"])
                conn.update(worksheet="Piloti", data=df)
            return df
        except Exception:
            # Se il foglio non esiste o è nuovo
            df = pd.DataFrame(columns=["ID", "Nome", "Peso", "Livello", "Moto", "Note"])
            return df

    @staticmethod
    def get_piloti_options():
        df = SuspensionDB.init_db()
        if df.empty:
            return []
        # Crea una lista di stringhe "Nome (ID)"
        return [f"{row['Nome']} ({row['ID']})" for _, row in df.iterrows()]

    @staticmethod
    def get_pilota_info(id_pilota):
        df = SuspensionDB.init_db()
        row = df[df['ID'] == id_pilota]
        if not row.empty:
            return row.iloc[0].to_dict()
        return None

    @staticmethod
    def add_pilota(nome, peso, livello, moto, note):
        conn = SuspensionDB.get_connection()
        df = SuspensionDB.init_db()
        
        # Genera ID univoco (iniziali + timestamp breve)
        new_id = f"{nome[:3].upper()}{int(datetime.now().timestamp())}"[-6:]
        
        new_row = pd.DataFrame([{
            "ID": new_id,
            "Nome": nome,
            "Peso": peso,
            "Livello": livello,
            "Moto": moto,
            "Note": note
        }])
        
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Piloti", data=updated_df)
        st.toast(f"✅ Pilota {nome} aggiunto correttamente!")
        return new_id
