import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import json
import uuid

class SuspensionDB:
    @staticmethod
    def _get_conn():
        return st.connection("gsheets", type=GSheetsConnection)

    @staticmethod
    def _read_sheet(sheet_name):
        conn = SuspensionDB._get_conn()
        try:
            df = conn.read(worksheet=sheet_name, ttl=0)
            return df if not df.empty else pd.DataFrame()
        except: return pd.DataFrame()

    @staticmethod
    def _write_sheet(sheet_name, df):
        conn = SuspensionDB._get_conn()
        conn.update(worksheet=sheet_name, data=df)

    @staticmethod
    def get_piloti():
        df = SuspensionDB._read_sheet("Piloti")
        exp = ["ID", "Nome", "Peso", "Livello", "Telefono", "Note"]
        if df.empty: return pd.DataFrame(columns=exp)
        for c in exp: 
            if c not in df.columns: df[c] = ""
        df["ID"] = df["ID"].astype(str)
        return df

    @staticmethod
    def get_garage(pid=None):
        df = SuspensionDB._read_sheet("Garage")
        exp = ["id_mezzo", "id_pilota", "tipo", "marca", "modello", "anno", "forcella_modello", "mono_modello"]
        if df.empty: return pd.DataFrame(columns=exp)
        for c in exp: 
            if c not in df.columns: df[c] = ""
        df["id_pilota"] = df["id_pilota"].astype(str)
        df["id_mezzo"] = df["id_mezzo"].astype(str)
        if pid: return df[df["id_pilota"] == str(pid)]
        return df

    @staticmethod
    def get_sessioni(mid):
        df = SuspensionDB._read_sheet("Sessioni")
        exp = ["id_sessione", "id_mezzo", "data", "pista_luogo", "condizione", "feedback_text", "rating", "dati_tecnici_json"]
        if df.empty: return pd.DataFrame(columns=exp)
        for c in exp: 
            if c not in df.columns: df[c] = ""
        df["id_mezzo"] = df["id_mezzo"].astype(str)
        f = df[df["id_mezzo"] == str(mid)]
        return f.sort_values(by="data", ascending=False) if not f.empty else f

    @staticmethod
    def save_session(mid, pista, cond, feed, rat, tech):
        df = SuspensionDB._read_sheet("Sessioni")
        exp = ["id_sessione", "id_mezzo", "data", "pista_luogo", "condizione", "feedback_text", "rating", "dati_tecnici_json"]
        if df.empty: df = pd.DataFrame(columns=exp)
        nr = pd.DataFrame([{
            "id_sessione": datetime.now().strftime("%Y%m%d%H%M%S"),
            "id_mezzo": str(mid), "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "pista_luogo": pista, "condizione": cond, "feedback_text": feed, "rating": rat,
            "dati_tecnici_json": json.dumps(tech)
        }])
        SuspensionDB._write_sheet("Sessioni", pd.concat([nr, df], ignore_index=True))

    @staticmethod
    def parse_json(s):
        try: return json.loads(s)
        except: return {}
