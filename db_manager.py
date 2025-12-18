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
        """Inizializza il DB e TRADUCE i nomi delle colonne vecchi in nuovi"""
        conn = SuspensionDB.get_connection()
        try:
            # Legge il foglio grezzo
            df = conn.read(worksheet="Piloti", ttl=0)
            
            # --- TRADUTTORE INTELLIGENTE ---
            # Mappa per convertire i nomi vecchi (del tuo foglio) nei nomi nuovi (dell'app)
            # A sinistra come sono nel tuo file, a destra come servono all'app
            mappa_traduzione = {
                "nome_completo": "Nome",  # Vecchio nome -> Nuovo nome
                "id_pilota": "ID",
                "peso_kg": "Peso",
                "livello": "Livello",
                "telefono": "Telefono",
                "note_fisiche": "Note",
                "moto_attuale": "Moto",
                "moto": "Moto",           # Varianti minuscole
                "nome": "Nome",
                "peso": "Peso"
            }
            
            # Rinomina le colonne se trova quelle vecchie
            df = df.rename(columns=mappa_traduzione)
            
            # Se il foglio è vuoto o mancano colonne critiche dopo la traduzione
            required_cols = ["ID", "Nome", "Telefono", "Peso", "Livello", "Moto", "Note"]
            
            # Aggiunge le colonne mancanti (vuote) per evitare crash
            for col in required_cols:
                if col not in df.columns:
                    df[col] = "" 
            
            # Ritorna solo le colonne che ci servono, nell'ordine giusto
            return df[required_cols]
            
        except Exception as e:
            # Se tutto fallisce, ritorna un dataframe vuoto ma con la struttura giusta
            return pd.DataFrame(columns=["ID", "Nome", "Telefono", "Peso", "Livello", "Moto", "Note"])

    @staticmethod
    def get_piloti_options():
        df = SuspensionDB.init_db()
        if df.empty:
            return []
        
        # Filtra via righe vuote o senza nome
        df = df[df["Nome"].notna() & (df["Nome"] != "")]
        
        # Crea la lista per il menu a tendina
        return [f"{row['Nome']} ({row['ID']})" for _, row in df.iterrows()]

    @staticmethod
    def get_pilota_info(id_pilota):
        df = SuspensionDB.init_db()
        # Cerca il pilota per ID
        row = df[df['ID'] == id_pilota]
        if not row.empty:
            return row.iloc[0].to_dict()
        return None

    @staticmethod
    def add_pilota(nome, peso, livello, telefono, note):
        conn = SuspensionDB.get_connection()
        df = SuspensionDB.init_db()
        
        # Crea ID univoco
        new_id = f"{nome[:3].upper()}{int(datetime.now().timestamp())}"[-6:]
        
        new_row = pd.DataFrame([{
            "ID": new_id,
            "Nome": nome,
            "Telefono": telefono,
            "Peso": peso,
            "Livello": livello,
            "Moto": "", 
            "Note": note
        }])
        
        # Unisce e salva
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # --- SALVATAGGIO COMPATIBILE ---
        # Prima di salvare su Google, se preferisci mantenere i nomi vecchi nel file,
        # potremmo ritradurli al contrario, ma per ora salviamo col formato NUOVO (Nome, Peso, ecc)
        # così si standardizza tutto piano piano.
        conn.update(worksheet="Piloti", data=updated_df)
        return new_id

    # --- GESTIONE MOTO (GARAGE) ---
    @staticmethod
    def get_mezzi_by_pilota(id_pilota):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Garage", ttl=0)
            if df.empty: return []
            
            # Rinomina colonne Garage se necessario
            df = df.rename(columns={"id_pilota": "ID_Pilota", "modello": "Modello", "tipo": "Tipo", "marca": "Marca", "anno": "Anno"})
            
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
    
    # --- GESTIONE SESSIONI (STORICO) ---
    @staticmethod
    def save_session(id_mezzo, pista, condizione, feedback, rating, dati_tecnici):
        conn = SuspensionDB.get_connection()
        try:
            df = conn.read(worksheet="Sessioni", ttl=0)
        except:
            df = pd.DataFrame(columns=["data", "id_mezzo", "pista_luogo", "condizione", "feedback_text", "rating", "dati_tecnici_json"])

        import json
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
            df = conn.read(worksheet="Sessioni", ttl=0)
            if df.empty: return pd.DataFrame()
            return df[df['id_mezzo'] == id_mezzo].sort_values(by="data", ascending=False)
        except:
            return pd.DataFrame()
