import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import uuid

class SuspensionDB:
    # --- UTILS ---
    @staticmethod
    def _get_conn():
        return st.connection("gsheets", type=GSheetsConnection)

    @staticmethod
    def _read_sheet(sheet_name):
        conn = SuspensionDB._get_conn()
        try:
            df = conn.read(worksheet=sheet_name, ttl=0)
            return df if not df.empty else pd.DataFrame()
        except:
            return pd.DataFrame()

    @staticmethod
    def _write_sheet(sheet_name, df):
        conn = SuspensionDB._get_conn()
        try:
            conn.update(worksheet=sheet_name, data=df)
        except Exception as e:
            st.error(f"Errore scrittura DB ({sheet_name}): {e}")

    # --- 1. GESTIONE PILOTI ---
    @staticmethod
    def get_piloti():
        df = SuspensionDB._read_sheet("Piloti")
        required = ["ID", "Nome", "Peso", "Livello", "Telefono", "Note"]
        
        if df.empty: 
            return pd.DataFrame(columns=required)
        
        # Assicuriamo che le colonne esistano tutte
        for col in required:
            if col not in df.columns: df[col] = ""
            
        # ID deve essere stringa per i confronti
        df["ID"] = df["ID"].astype(str)
        return df

    @staticmethod
    def add_pilota(nome, peso, livello, telefono, note):
        df = SuspensionDB.get_piloti()
        new_row = pd.DataFrame([{
            "ID": str(uuid.uuid4())[:8],
            "Nome": nome,
            "Peso": peso,
            "Livello": livello,
            "Telefono": telefono,
            "Note": note
        }])
        
        updated = pd.concat([df, new_row], ignore_index=True)
        SuspensionDB._write_sheet("Piloti", updated)
        st.toast(f"Pilota {nome} creato!", icon="✅")

    # --- 2. GESTIONE GARAGE (Moto) ---
    @staticmethod
    def get_garage(id_pilota=None):
        df = SuspensionDB._read_sheet("Garage")
        required = ["id_mezzo", "id_pilota", "tipo", "marca", "modello", "anno", "forcella_modello", "mono_modello"]
        
        if df.empty: return pd.DataFrame(columns=required)
        for col in required:
            if col not in df.columns: df[col] = ""
        
        df["id_pilota"] = df["id_pilota"].astype(str)
        df["id_mezzo"] = df["id_mezzo"].astype(str)
        
        if id_pilota:
            return df[df["id_pilota"] == str(id_pilota)]
        return df

    @staticmethod
    def add_mezzo(id_pilota, tipo, marca, modello, anno, forc_mod, mono_mod):
        df = SuspensionDB.get_garage()
        new_row = pd.DataFrame([{
            "id_mezzo": str(uuid.uuid4())[:8],
            "id_pilota": str(id_pilota),
            "tipo": tipo,
            "marca": marca,
            "modello": modello,
            "anno": anno,
            "forcella_modello": forc_mod,
            "mono_modello": mono_mod
        }])
        updated = pd.concat([df, new_row], ignore_index=True)
        SuspensionDB._write_sheet("Garage", updated)
        st.toast(f"Moto aggiunta al garage!", icon="🏍️")

    # --- 3. GESTIONE SESSIONI (Setup & Feedback) ---
    @staticmethod
    def get_sessioni(id_mezzo):
        df = SuspensionDB._read_sheet("Sessioni")
        required = ["id_sessione", "id_mezzo", "data", "pista_luogo", "condizione", "feedback_text", "rating", "dati_tecnici_json"]
        
        if df.empty: return pd.DataFrame(columns=required)
        for col in required:
            if col not in df.columns: df[col] = ""
            
        df["id_mezzo"] = df["id_mezzo"].astype(str)
        
        # Filtra e ordina
        filtered = df[df["id_mezzo"] == str(id_mezzo)]
        if not filtered.empty and "data" in filtered.columns:
             return filtered.sort_values(by="data", ascending=False)
        return filtered

    @staticmethod
    def save_session(id_mezzo, pista, cond, feedback, rating, tech_data):
        df = SuspensionDB.get_sessioni(None) # Carica tutto per appendere
        
        new_row = pd.DataFrame([{
            "id_sessione": datetime.now().strftime("%Y%m%d%H%M%S"),
            "id_mezzo": str(id_mezzo),
            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "pista_luogo": pista,
            "condizione": cond,
            "feedback_text": feedback,
            "rating": rating,
            "dati_tecnici_json": json.dumps(tech_data)
        }])
        
        # Se il DF originale è vuoto, usa new_row, altrimenti concatena
        if df.empty:
            updated = new_row
        else:
            updated = pd.concat([new_row, df], ignore_index=True)
            
        SuspensionDB._write_sheet("Sessioni", updated)
        st.toast("✅ Sessione Salvata!", icon="🏁")

    @staticmethod
    def parse_json(json_str):
        try: return json.loads(json_str)
        except: return {}
