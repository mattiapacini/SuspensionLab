import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import uuid

class SuspensionDB:
    @staticmethod
    def get_connection():
        return st.connection("gsheets", type=GSheetsConnection)

    # --- 1. GESTIONE PILOTI (ANAGRAFICA) ---
    @staticmethod
    def get_piloti_options():
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Piloti", ttl=0)
            # Mappatura colonne piloti (per sicurezza)
            mappa = {
                "nome_completo": "Nome", "id_pilota": "ID", 
                "peso_kg": "Peso", "livello": "Livello", 
                "telefono": "Telefono", "note_fisiche": "Note"
            }
            # Normalizza nomi
            df.columns = [c.strip().lower() for c in df.columns]
            df = df.rename(columns={k.lower(): v for k, v in mappa.items()})
            
            # Se trova la colonna Nome e ID
            if "nome" in df.columns and "id" in df.columns:
                 df = df[df["nome"].notna() & (df["nome"] != "")]
                 return [f"{row['nome']} ({row['id']})" for _, row in df.iterrows()]
            return []
        except:
            return []

    @staticmethod
    def add_pilota(nome, peso, livello, telefono, note):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Piloti", ttl=0)
        except:
             # Struttura base se vuoto
             df = pd.DataFrame(columns=["id_pilota", "nome_completo", "telefono", "peso_kg", "livello", "note_fisiche"])

        new_id = f"{nome[:3].upper()}{int(datetime.now().timestamp())}"[-6:]
        
        # Usa i nomi colonne che probabilmente hai nel foglio Piloti
        new_row = pd.DataFrame([{
            "id_pilota": new_id, 
            "nome_completo": nome, 
            "telefono": telefono,
            "peso_kg": peso, 
            "livello": livello, 
            "note_fisiche": note
        }])
        
        updated = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Piloti", data=updated)
        return new_id

    # --- 2. GESTIONE GARAGE (CON LE TUE COLONNE ESATTE) ---
    @staticmethod
    def get_mezzi_by_pilota(id_pilota):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Garage", ttl=0)
            
            # Assicura che id_pilota sia stringa per il confronto
            df['id_pilota'] = df['id_pilota'].astype(str)
            mezz = df[df['id_pilota'] == str(id_pilota)]
            
            lista = []
            for _, row in mezz.iterrows():
                # Crea la stringa per il menu a tendina
                nome_moto = f"{row['modello']} ({row['tipo']})"
                # Aggiungiamo l'ID mezzo nascosto nella stringa per recuperarlo dopo
                lista.append(f"{nome_moto} #{row['id_mezzo']}") 
            return lista
        except Exception as e:
            return []

    @staticmethod
    def add_mezzo(id_pilota, tipo, marca, modello, anno, forcella, mono):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Garage", ttl=0)
        except:
            # Crea struttura con le TUE colonne
            df = pd.DataFrame(columns=["id_mezzo", "id_pilota", "tipo", "marca", "modello", "anno", "forcella_modello", "mono_modello"])

        # Genera ID Mezzo univoco
        id_mezzo = f"M{int(datetime.now().timestamp())}"

        new_row = pd.DataFrame([{
            "id_mezzo": id_mezzo,
            "id_pilota": id_pilota,
            "tipo": tipo,
            "marca": marca,
            "modello": modello,
            "anno": anno,
            "forcella_modello": forcella,
            "mono_modello": mono
        }])
        
        updated = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Garage", data=updated)

    # --- 3. GESTIONE DIARIO / SESSIONI (CON LE TUE COLONNE ESATTE) ---
    @staticmethod
    def save_session(id_mezzo, pista, condizione, feedback, rating, dati_tecnici):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Sessioni", ttl=0) # O "Diario" se l'hai rinominato
        except:
            # Crea struttura con le TUE colonne
            cols = ["id_sessione", "id_mezzo", "data", "pista_luogo", "condizione", "feedback_text", "rating", "dati_tecnici_json"]
            df = pd.DataFrame(columns=cols)

        # Genera ID Sessione
        id_sessione = f"S{int(datetime.now().timestamp())}"

        new_row = pd.DataFrame([{
            "id_sessione": id_sessione,
            "id_mezzo": id_mezzo,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "pista_luogo": pista,
            "condizione": condizione,
            "feedback_text": feedback,
            "rating": rating,
            "dati_tecnici_json": json.dumps(dati_tecnici)
        }])
        
        updated = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Sessioni", data=updated) # Assicurati che il foglio si chiami "Sessioni" o "Diario"

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
