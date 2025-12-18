import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json

class SuspensionDB:
    @staticmethod
    def get_connection():
        return st.connection("gsheets", type=GSheetsConnection)

    @staticmethod
    def init_db():
        """Legge l'anagrafica Piloti e sistema i nomi delle colonne"""
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Piloti", ttl=0)
            
            # Mappa per capire i nomi delle colonne, vecchi o nuovi
            mappa = {
                "nome_completo": "Nome", "id_pilota": "ID", 
                "peso_kg": "Peso", "livello": "Livello", 
                "telefono": "Telefono", "note_fisiche": "Note"
            }
            
            # Normalizza nomi colonne (minuscolo e senza spazi)
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            df = df.rename(columns=mappa)
            
            # Assicura che le colonne essenziali esistano
            cols_finali = ["ID", "Nome", "Telefono", "Peso", "Livello", "Note"]
            for col in cols_finali:
                found = False
                for existing in df.columns:
                    if existing.lower() == col.lower():
                        df = df.rename(columns={existing: col})
                        found = True
                        break
                if not found:
                    df[col] = "" 

            return df
        except:
            return pd.DataFrame(columns=["ID", "Nome", "Telefono", "Peso", "Livello", "Note"])

    @staticmethod
    def get_piloti_options():
        df = SuspensionDB.init_db()
        if df.empty: return []
        df = df[df["Nome"] != ""]
        return [f"{row['Nome']} ({row['ID']})" for _, row in df.iterrows()]

    @staticmethod
    def add_pilota(nome, peso, livello, telefono, note):
        conn = SuspensionDB.get_connection()
        df = SuspensionDB.init_db()
        new_id = f"{nome[:3].upper()}{int(datetime.now().timestamp())}"[-6:]
        
        new_row = pd.DataFrame([{
            "ID": new_id, "Nome": nome, "Telefono": telefono,
            "Peso": peso, "Livello": livello, "Note": note
        }])
        
        # Salviamo nel foglio Piloti
        updated = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Piloti", data=updated)
        return new_id

    # --- GESTIONE GARAGE (STRETTA E PULITA) ---
    @staticmethod
    def get_mezzi_by_pilota(id_pilota):
        conn = SuspensionDB.get_connection()
        try:
            # Legge SOLO il foglio Garage
            df = conn.read(worksheet="Garage", ttl=0)
            
            # Pulisce i nomi delle colonne per sicurezza
            df.columns = [c.strip().lower() for c in df.columns]
            rename_map = {"id_pilota": "ID_Pilota", "modello": "Modello", "tipo": "Tipo"}
            df = df.rename(columns=rename_map)
            
            # Filtra le moto di quel pilota specifico
            # Converte entrambi in stringa per evitare errori di tipo
            moto_del_pilota = df[df['ID_Pilota'].astype(str) == str(id_pilota)]
            
            lista = []
            for _, row in moto_del_pilota.iterrows():
                modello = str(row.get('Modello', ''))
                tipo = str(row.get('Tipo', ''))
                if modello and modello != "nan":
                    lista.append(f"{modello} ({tipo})")
            
            return lista
        except Exception as e:
            # Se il foglio Garage non esiste o è vuoto, ritorna lista vuota
            return []

    @staticmethod
    def add_mezzo(id_pilota, tipo, marca, modello, anno, fork, mono):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Garage", ttl=0)
        except:
            # Se non esiste, crea la struttura
            df = pd.DataFrame(columns=["ID_Pilota", "Tipo", "Marca", "Modello", "Anno"])

        new_row = pd.DataFrame([{
            "ID_Pilota": id_pilota, "Tipo": tipo, "Marca": marca, 
            "Modello": modello, "Anno": anno
        }])
        
        updated = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Garage", data=updated)

    # --- GESTIONE SESSIONI / DIARIO (STRETTA E PULITA) ---
    @staticmethod
    def save_session(id_mezzo, pista, condizione, feedback, rating, dati_tecnici):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Sessioni", ttl=0)
        except:
            # Se non esiste, crea la struttura
            cols = ["data", "id_mezzo", "pista_luogo", "condizione", "feedback_text", "rating", "dati_tecnici_json"]
            df = pd.DataFrame(columns=cols)

        new_row = pd.DataFrame([{
            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "id_mezzo": id_mezzo, 
            "pista_luogo": pista,
            "condizione": condizione, 
            "feedback_text": feedback,
            "rating": rating, 
            "dati_tecnici_json": json.dumps(dati_tecnici)
        }])
        
        updated = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Sessioni", data=updated)

    @staticmethod
    def get_history_by_mezzo(id_mezzo):
        conn = SuspensionDB.get_connection()
        try:
            # Legge SOLO il foglio Sessioni
            df = conn.read(worksheet="Sessioni", ttl=0)
            if df.empty: return pd.DataFrame()
            
            # Filtra per la moto selezionata
            # Converte ID in stringa per sicurezza
            df['id_mezzo'] = df['id_mezzo'].astype(str)
            return df[df['id_mezzo'] == str(id_mezzo)].sort_values(by="data", ascending=False)
        except:
            return pd.DataFrame()
