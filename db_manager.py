import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime
import uuid

class SuspensionDB:
    
    @staticmethod
    def get_connection():
        return st.connection("gsheets", type=GSheetsConnection)

    @staticmethod
    def load_data(sheet_name):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet=sheet_name, ttl=0)
            df = df.dropna(how="all")
            return df
        except:
            return pd.DataFrame()

    # --- SCRITTURA (Create) ---
    @staticmethod
    def add_pilota(nome, peso, livello, telefono, note):
        conn = SuspensionDB.get_connection()
        df = SuspensionDB.load_data("PILOTI")
        nuovo_id = f"P{len(df) + 1:03d}"
        nuova_riga = pd.DataFrame([{
            "id_pilota": nuovo_id, "nome_completo": nome, "peso_kg": peso,
            "livello": livello, "telefono": telefono, "note_fisiche": note
        }])
        conn.update(worksheet="PILOTI", data=pd.concat([df, nuova_riga], ignore_index=True))
        return True

    @staticmethod
    def add_mezzo(id_pilota, tipo, marca, modello, anno, forcella, mono):
        conn = SuspensionDB.get_connection()
        df = SuspensionDB.load_data("GARAGE")
        nuovo_id = f"M{len(df) + 1:03d}"
        nuova_riga = pd.DataFrame([{
            "id_mezzo": nuovo_id, "id_pilota": id_pilota, "tipo": tipo,
            "marca": marca, "modello": modello, "anno": anno,
            "forcella_modello": forcella, "mono_modello": mono
        }])
        conn.update(worksheet="GARAGE", data=pd.concat([df, nuova_riga], ignore_index=True))
        return True

    @staticmethod
    def save_session(id_mezzo, pista, condizione, feedback, rating, dati_tecnici):
        conn = SuspensionDB.get_connection()
        df = SuspensionDB.load_data("DIARIO")
        new_row = pd.DataFrame([{
            "id_sessione": str(uuid.uuid4())[:8],
            "id_mezzo": id_mezzo,
            "data": datetime.now().strftime("%Y-%m-%d"),
            "pista_luogo": pista,
            "condizione": condizione,
            "feedback_text": feedback,
            "rating": rating,
            "dati_tecnici_json": json.dumps(dati_tecnici)
        }])
        conn.update(worksheet="DIARIO", data=pd.concat([df, new_row], ignore_index=True))
        return True

    # --- LETTURA (Read) - NUOVA INTEGRAZIONE ---
    @staticmethod
    def get_piloti_options():
        df = SuspensionDB.load_data("PILOTI")
        if df.empty: return []
        return [f"{row['nome_completo']} ({row['id_pilota']})" for _, row in df.iterrows()]

    @staticmethod
    def get_mezzi_by_pilota(id_pilota):
        df = SuspensionDB.load_data("GARAGE")
        if df.empty: return []
        filtered = df[df['id_pilota'] == id_pilota]
        return [f"{row['modello']} - {row['tipo']} ({row['id_mezzo']})" for _, row in filtered.iterrows()]

    @staticmethod
    def get_history_by_mezzo(id_mezzo):
        """Recupera tutte le sessioni passate di una specifica moto"""
        df = SuspensionDB.load_data("DIARIO")
        if df.empty: return pd.DataFrame()
        # Filtra per ID moto
        filtered = df[df['id_mezzo'] == id_mezzo]
        # Ordina dalla più recente
        return filtered.sort_values(by="data", ascending=False)
