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
        """Inizializza il DB e normalizza i nomi delle colonne"""
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Piloti", ttl=0)
            
            # Se il foglio è vuoto o nuovo, creiamo la struttura corretta
            if df.empty or len(df.columns) < 2:
                df = pd.DataFrame(columns=["ID", "Nome", "Telefono", "Peso", "Livello", "Moto", "Note"])
                conn.update(worksheet="Piloti", data=df)
                return df
            
            # ⚠️ AUTO-CORREZIONE COLONNE (Per non perdere i vecchi dati)
            # Rinominiamo le vecchie colonne (es. 'nome_completo') in quelle nuove ('Nome')
            rename_map = {
                "nome_completo": "Nome",
                "id_pilota": "ID",
                "peso_kg": "Peso",
                "livello": "Livello",
                "telefono": "Telefono",
                "note_fisiche": "Note",
                "moto_attuale": "Moto"
            }
            df = df.rename(columns=rename_map)
            
            # Assicuriamoci che tutte le colonne necessarie esistano
            required_cols = ["ID", "Nome", "Telefono", "Peso", "Livello", "Moto", "Note"]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = "" # Crea colonna vuota se manca
            
            return df
            
        except Exception as e:
            # Fallback di emergenza
            return pd.DataFrame(columns=["ID", "Nome", "Telefono", "Peso", "Livello", "Moto", "Note"])

    @staticmethod
    def get_piloti_options():
        df = SuspensionDB.init_db()
        if df.empty:
            return []
        
        # Filtra solo righe con un nome valido
        df = df[df["Nome"].notna() & (df["Nome"] != "")]
        
        # Crea lista dropdown
        return [f"{row['Nome']} ({row['ID']})" for _, row in df.iterrows()]

    @staticmethod
    def get_pilota_info(id_pilota):
        df = SuspensionDB.init_db()
        row = df[df['ID'] == id_pilota]
        if not row.empty:
            return row.iloc[0].to_dict()
        return None

    @staticmethod
    def add_pilota(nome, peso, livello, telefono, note):
        conn = SuspensionDB.get_connection()
        df = SuspensionDB.init_db()
        
        # Genera ID
        new_id = f"{nome[:3].upper()}{int(datetime.now().timestamp())}"[-6:]
        
        new_row = pd.DataFrame([{
            "ID": new_id,
            "Nome": nome,
            "Telefono": telefono,
            "Peso": peso,
            "Livello": livello,
            "Moto": "", # La moto si aggiunge dal garage
            "Note": note
        }])
        
        # Concatena e salva (gestione pandas aggiornata)
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Piloti", data=updated_df)
        return new_id

    @staticmethod
    def get_mezzi_by_pilota(id_pilota):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Garage", ttl=0)
            if df.empty: return []
            
            # Filtra per ID pilota
            mezz = df[df['ID_Pilota'] == id_pilota]
            return [f"{row['Modello']} ({row['Tipo']})" for _, row in mezz.iterrows()]
        except:
            return []

    @staticmethod
    def add_mezzo(id_pilota, tipo, marca, modello, anno, fork, mono):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Garage", ttl=0)
        except:
            df = pd.DataFrame(columns=["ID_Pilota", "Tipo", "Marca", "Modello", "Anno"])

        new_row = pd.DataFrame([{
            "ID_Pilota": id_pilota,
            "Tipo": tipo,
            "Marca": marca,
            "Modello": modello,
            "Anno": anno
        }])
        
        updated = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Garage", data=updated)
