import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(layout="wide")
st.title("🕵️‍♂️ DEBUGGING SESSION")

# 1. VERIFICA LIBRERIE
st.write("Checking libraries...")
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    st.success("✅ Libreria caricata correttamente.")
except Exception as e:
    st.error("❌ Errore Libreria")
    st.exception(e)
    st.stop()

# 2. VERIFICA LETTURA DIRETTA
st.write("Attempting to read Google Sheet...")

try:
    # Proviamo a leggere il foglio 'PILOTI' senza cache (ttl=0)
    df = conn.read(worksheet="PILOTI", ttl=0)
    
    st.success("✅ CONNESSIONE RIUSCITA!")
    st.write("Ecco i dati trovati:")
    st.dataframe(df)
    
except Exception as e:
    st.error("❌ CONNESSIONE FALLITA")
    st.warning("Leggi attentamente il messaggio qui sotto:")
    # Questo stamperà l'errore tecnico preciso
    st.code(str(e))
    
    # Aiuto alla diagnosi in base all'errore
    err_msg = str(e)
    if "403" in err_msg or "PERMISSION_DENIED" in err_msg:
        st.markdown("### 🔒 DIAGNOSI: Permesso Negato")
        st.write("Il 'robot' non ha il permesso di entrare.")
        st.write("1. Copia questa email: `python-app@suspensionlab2.iam.gserviceaccount.com`")
        st.write("2. Vai sul foglio Google -> Tasto Condividi -> Incollala come EDITOR.")
    elif "WorksheetNotFound" in err_msg:
        st.markdown("### 📄 DIAGNOSI: Foglio non trovato")
        st.write("Il codice cerca una linguetta chiamata esattamente `PILOTI`.")
        st.write("Controlla che nel tuo Excel in basso a sinistra ci sia scritto `PILOTI` (tutto maiuscolo, niente spazi).")
    elif "404" in err_msg:
        st.markdown("### 🔗 DIAGNOSI: Link Sbagliato")
        st.write("Il link nel file secrets.toml non è corretto o il file non esiste.")
