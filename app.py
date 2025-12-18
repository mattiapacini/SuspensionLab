import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(layout="wide")
st.title("🧪 TEST PUBBLICO")

st.info("Assicurati di aver messo il foglio Google su 'Chiunque abbia il link' -> 'Editor' per questo test.")

try:
    # Creiamo la connessione
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Proviamo a leggere. ttl=0 forza la rilettura
    df = conn.read(worksheet="PILOTI", ttl=0)
    
    st.success("✅ SUCCESSO! I dati sono stati letti:")
    st.dataframe(df)
    st.balloons()
    
except Exception as e:
    st.error("❌ ANCORA ERRORE")
    st.write("Ecco il codice tecnico dell'errore (copia questo):")
    # Questo comando stampa la "carta d'identità" dell'errore
    st.code(repr(e))
