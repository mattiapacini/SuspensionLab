import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json

class SuspensionDB:
    @staticmethod
    def get_connection():
        return st.connection("gsheets", type=GSheetsConnection)

    # --- 1. GESTIONE PILOTI ---
    @staticmethod
    def get_piloti_options():
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Piloti", ttl=0)
            # Pulisce nomi colonne
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            
            # Mappa flessibile
            rename_map = {
                "nome_completo": "Nome", "nome": "Nome",
                "id_pilota": "ID", "id": "ID"
            }
            df = df.rename(columns=rename_map)
            
            if "Nome" in df.columns and "ID" in df.columns:
                 df = df[df["Nome"].notna() & (df["Nome"] != "")]
                 return [f"{row['Nome']} ({row['ID']})" for _, row in df.iterrows()]
            return []
        except:
            return []

    @staticmethod
    def add_pilota(nome, peso, livello, telefono, note):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Piloti", ttl=0)
        except:
             df = pd.DataFrame(columns=["id_pilota", "nome_completo", "telefono", "peso_kg", "livello", "note_fisiche"])

        new_id = f"{nome[:3].upper()}{int(datetime.now().timestamp())}"[-6:]
        
        new_row = pd.DataFrame([{
            "id_pilota": new_id, "nome_completo": nome, "telefono": telefono,
            "peso_kg": peso, "livello": livello, "note_fisiche": note
        }])
        
        updated = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Piloti", data=updated)
        return new_id

    # --- 2. GESTIONE GARAGE (FIX NAN) ---
    @staticmethod
    def get_mezzi_by_pilota(id_pilota):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Garage", ttl=0)
            
            # Normalizza colonne
            df.columns = [c.strip().lower() for c in df.columns]
            
            # Filtra per pilota
            df['id_pilota'] = df['id_pilota'].astype(str)
            mezz = df[df['id_pilota'] == str(id_pilota)]
            
            lista = []
            for _, row in mezz.iterrows():
                # Gestione sicura dei dati mancanti (NO PIÙ "nan")
                marca = str(row.get('marca', '')).replace('nan', '').strip()
                modello = str(row.get('modello', '')).replace('nan', '').strip()
                tipo = str(row.get('tipo', 'MOTO')).replace('nan', 'MOTO')
                id_m = str(row.get('id_mezzo', ''))

                # Se modello è vuoto, mettiamo un placeholder
                if not modello: modello = "Modello Sconosciuto"
                
                # Costruisce la stringa bella
                nome_display = f"{marca} {modello} ({tipo})".strip()
                lista.append(f"{nome_display} #{id_m}") 
            return lista
        except Exception as e:
            return []

    @staticmethod
    def add_mezzo(id_pilota, tipo, marca, modello, anno, forcella, mono):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Garage", ttl=0)
        except:
            df = pd.DataFrame(columns=["id_mezzo", "id_pilota", "tipo", "marca", "modello", "anno", "forcella_modello", "mono_modello"])

        id_mezzo = f"M{int(datetime.now().timestamp())}"

        new_row = pd.DataFrame([{
            "id_mezzo": id_mezzo, "id_pilota": id_pilota, "tipo": tipo,
            "marca": marca, "modello": modello, "anno": anno,
            "forcella_modello": forcella, "mono_modello": mono
        }])
        
        updated = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Garage", data=updated)

    # --- 3. GESTIONE SESSIONI ---
    @staticmethod
    def save_session(id_mezzo, pista, condizione, feedback, rating, dati_tecnici):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Sessioni", ttl=0)
        except:
            cols = ["id_sessione", "id_mezzo", "data", "pista_luogo", "condizione", "feedback_text", "rating", "dati_tecnici_json"]
            df = pd.DataFrame(columns=cols)

        id_sessione = f"S{int(datetime.now().timestamp())}"

        new_row = pd.DataFrame([{
            "id_sessione": id_sessione, "id_mezzo": id_mezzo,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "pista_luogo": pista, "condizione": condizione,
            "feedback_text": feedback, "rating": rating,
            "dati_tecnici_json": json.dumps(dati_tecnici)
        }])
        
        updated = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Sessioni", data=updated)

    @staticmethod
    def get_history_by_mezzo(id_mezzo):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Sessioni", ttl=0)
            if df.empty: return pd.DataFrame()
            df['id_mezzo'] = df['id_mezzo'].astype(str)
            return df[df['id_mezzo'] == str(id_mezzo)].sort_values(by="data", ascending=False)
        except:
            return pd.DataFrame()
