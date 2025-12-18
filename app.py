import streamlit as st
import pandas as pd
import numpy as np
import json
# Assicurati che il file db_manager.py sia nella stessa cartella
try:
    from db_manager import SuspensionDB
except ImportError:
    st.error("⚠️ Manca il file 'db_manager.py'. Crealo incollando il codice del database.")
    st.stop()

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Suspension Lab V7", 
    page_icon="🔧", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZZATO ---
st.markdown("""
<style>
    div.stButton > button {
        height: 3em;
        font-weight: bold;
        width: 100%;
    }
    [data-testid="stSidebar"] {
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. BARRA LATERALE: GESTIONE LAVORO
# ==============================================================================
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    
    # CARICAMENTO PILOTI DAL DATABASE
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except Exception as e:
        st.error(f"Errore DB: {e}")
        lista_piloti = ["Errore Connessione"]

    # Selettore Pilota
    pilota_sel = st.selectbox("👤 Pilota", ["Seleziona..."] + lista_piloti)
    
    # Selettore Mezzo (Appare solo se hai scelto un pilota)
    mezzo_sel = None
    if pilota_sel != "Seleziona..." and pilota_sel != "Errore Connessione":
        try:
            # Estrae l'ID: "Mario (P001)" -> "P001"
            id_pilota = pilota_sel.split("(")[-1].replace(")", "")
            lista_mezzi = SuspensionDB.get_mezzi_by_pilota(id_pilota)
            mezzo_sel = st.selectbox("🏍️ Mezzo", ["Nuovo Mezzo..."] + lista_mezzi)
        except:
            st.warning("Nessun mezzo trovato o errore lettura.")

    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.button("➕ Pilota")
    c2.button("➕ Mezzo")

# ==============================================================================
# 2. INTESTAZIONE DINAMICA
# ==============================================================================
if mezzo_sel and mezzo_sel != "Nuovo Mezzo...":
    # Parsing stringa: "CRF 450 - MOTO (M001)"
    nome_mezzo = mezzo_sel.split("(")[0]
    tipo_mezzo = "MOTO" if "MOTO" in mezzo_sel else "MTB"
    
    st.markdown(f"""
    ## 🛠️ {nome_mezzo}
    <span style='background-color:#e6ffe6; padding:4px; border-radius:4px; color:green; font-weight:bold; font-size:0.8em'>{tipo_mezzo}</span>
    """, unsafe_allow_html=True)
else:
    st.title("🛠️ Suspension Lab")
    st.info("👈 Seleziona un Pilota dal menu laterale per iniziare.")

st.markdown("---")

# ==============================================================================
# 3. AREA DI LAVORO (WORKBENCH)
# ==============================================================================
if mezzo_sel and mezzo_sel != "Nuovo Mezzo...":
    
    tab_setup, tab_sim, tab_diario = st.tabs(["🔧 SETUP FISICO", "📈 SIMULATORE", "📝 DIARIO"])

    with tab_setup:
        st.caption("Configurazione Hardware Attuale")
        col_A, col_B = st.columns([1, 1])
        
        with col_A:
            st.subheader("Geometria")
            d_clamp = st.slider("Clamp Ø (mm)", 8.0, 22.0, 12.0, step=0.5)
            d_pistone = st.number_input("Pistone Ø (mm)", value=50.0)

        with col_B:
            st.subheader("Molle & Precarichi")
            if "MOTO" in mezzo_sel:
                k_molla = st.number_input("Molla (N/mm)", value=4.8, step=0.1)
                st.info(f"Rider Sag Target: ~105 mm")
            else:
                psi_main = st.number_input("Aria (PSI)", value=85, step=5)
                token = st.slider("Token", 0, 5, 2)

    with tab_sim:
        st.subheader("Analisi Idraulica")
        st.write("🔧 Simulazione ReStackor (Placeholder)")
        # Qui un giorno collegheremo il calcolo vero
        st.line_chart([0, 5, 15, 40, 90, 160]) 

    with tab_diario:
        st.subheader("Nuova Sessione")
        with st.form("form_sessione"):
            c1, c2 = st.columns(2)
            pista = c1.text_input("Pista / Luogo")
            condizione = c2.selectbox("Condizione", ["Secco", "Fango", "Sabbia", "Sassi"])
            feedback = st.text_area("Feedback Pilota")
            rating = st.slider("Voto Setup", 1, 5, 3)
            
            submitted = st.form_submit_button("💾 SALVA NEL CLOUD")
            
            if submitted:
                # Creiamo un pacchetto dati finto per ora
                dati_tecnici = {"click_comp": 12, "click_reb": 14, "notes": "Test salvataggio"}
                
                # Chiamata al Database
                try:
                    # Estraiamo l'ID mezzo pulito: "CRF... (M001)" -> "M001"
                    id_mezzo_clean = mezzo_sel.split("(")[-1].replace(")", "")
                    
                    SuspensionDB.save_session(id_mezzo_clean, pista, condizione, feedback, rating, dati_tecnici)
                    st.success("Sessione salvata su Google Sheets!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Errore salvataggio: {e}")
