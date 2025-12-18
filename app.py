import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- IMPORT MODULI ---
try:
    from db_manager import SuspensionDB
    from physics import SuspensionPhysics
except ImportError:
    st.error("⚠️ ERRORE CRITICO: I file db_manager.py o physics.py mancano o hanno errori.")
    st.stop()

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="SuspensionLab Pro", page_icon="🔧", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 5px; }
    [data-testid="stSidebar"] { background-color: #f0f2f6; }
    h1 { color: #2c3e50; }
</style>
""", unsafe_allow_html=True)

# --- INIZIALIZZA SESSIONE ---
if "autenticato" not in st.session_state: st.session_state["autenticato"] = False
if "pilota_selezionato" not in st.session_state: st.session_state["pilota_selezionato"] = None

# --- LOGIN (Semplificato per ora) ---
if not st.session_state["autenticato"]:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🔒 SuspensionLab")
        pwd = st.text_input("Password Accesso", type="password")
        if st.button("ENTRA", type="primary"):
            if pwd == "sospensioni2025": # Password
                st.session_state["autenticato"] = True
                st.rerun()
            else:
                st.error("Password errata")
    st.stop()

# --- SIDEBAR: SELEZIONE PILOTA ---
with st.sidebar:
    st.title("📂 NAVIGATORE")
    
    # Carica lista piloti
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except Exception as e:
        st.error(f"Errore DB: {e}")
        lista_piloti = []

    scelta = st.selectbox("Seleziona Pilota", ["..."] + lista_piloti)
    
    if choice := scelta:
        if choice != "...":
            st.session_state["pilota_selezionato"] = choice.split("(")[-1].replace(")", "")
            st.success(f"Pilota attivo: {choice.split('(')[0]}")
    
    st.markdown("---")
    if st.button("Logout"):
        st.session_state["autenticato"] = False
        st.rerun()

# --- MAIN PAGE ---
st.title("🔧 SuspensionLab Officer")

tab_clienti, tab_setup, tab_sim = st.tabs(["👥 GESTIONE CLIENTI", "📝 SETUP MOTO", "📊 SIMULATORE"])

# --- TAB 1: GESTIONE CLIENTI (INSERIMENTO) ---
with tab_clienti:
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("➕ Nuovo Cliente")
        with st.form("form_nuovo_pilota", clear_on_submit=True):
            nome = st.text_input("Nome e Cognome*")
            col_a, col_b = st.columns(2)
            peso = col_a.number_input("Peso (kg)", 40, 150, 75)
            livello = col_b.selectbox("Livello", ["Amatore", "Esperto", "Pro", "Agonista"])
            moto = st.text_input("Moto (Marca Modello Anno)")
            note = st.text_area("Note iniziali")
            
            submitted = st.form_submit_button("💾 SALVA CLIENTE", type="primary")
            
            if submitted:
                if nome:
                    try:
                        SuspensionDB.add_pilota(nome, peso, livello, moto, note)
                        st.success(f"Cliente {nome} salvato nel Database!")
                        st.rerun() # Ricarica per aggiornare la lista a sinistra
                    except Exception as e:
                        st.error(f"Errore salvataggio: {e}")
                else:
                    st.warning("Il nome è obbligatorio.")

    with c2:
        st.subheader("📋 Dettagli Pilota Selezionato")
        if st.session_state["pilota_selezionato"]:
            info = SuspensionDB.get_pilota_info(st.session_state["pilota_selezionato"])
            if info:
                st.json(info)
        else:
            st.info("👈 Seleziona un pilota dalla barra laterale per vedere i dettagli.")

# --- TAB 2: SETUP (Placeholder) ---
with tab_setup:
    if st.session_state["pilota_selezionato"]:
        st.write("Qui andrà la scheda setup...")
    else:
        st.warning("Seleziona prima un pilota.")

# --- TAB 3: SIMULATORE (Placeholder veloce) ---
with tab_sim:
    st.info("Il simulatore grafico apparirà qui una volta selezionato il setup.")
