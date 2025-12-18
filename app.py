import streamlit as st
import pandas as pd
import numpy as np
import json
# Assicurati che il file db_manager.py sia nella stessa cartella
from db_manager import SuspensionDB 

# --- CONFIGURAZIONE PAGINA (Mobile Friendly) ---
st.set_page_config(
    page_title="Suspension Lab V7", 
    page_icon="🔧", 
    layout="wide",
    initial_sidebar_state="collapsed" # Su mobile parte chiusa per pulizia
)

# --- CSS PERSONALIZZATO (Per i pulsanti grossi su mobile) ---
st.markdown("""
<style>
    div.stButton > button {
        height: 3em;  /* Pulsanti più alti per dita sporche */
        font-weight: bold;
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
    st.header("🗂️ ARCHIVIO")
    
    # 1. Carica lista Piloti dal Database Google
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except Exception as e:
        st.error("Errore connessione DB")
        lista_piloti = []

    # Selettore Pilota
    pilota_sel = st.selectbox("👤 Pilota", ["Seleziona..."] + lista_piloti)
    
    # 2. Seleziona Mezzo (solo se pilota selezionato)
    if pilota_sel != "Seleziona...":
        # Estrae l'ID tra parentesi: "Mario (P001)" -> "P001"
        id_pilota = pilota_sel.split("(")[-1].replace(")", "")
        lista_mezzi = SuspensionDB.get_mezzi_by_pilota(id_pilota)
        mezzo_sel = st.selectbox("🏍️ Mezzo", ["Nuovo Mezzo..."] + lista_mezzi)
    else:
        mezzo_sel = None

    st.markdown("---")
    
    # Pulsanti Azione Rapida
    c1, c2 = st.columns(2)
    c1.button("➕ Nuovo Pilota")
    c2.button("➕ Nuovo Mezzo")

# ==============================================================================
# 2. INTESTAZIONE DINAMICA
# ==============================================================================
# Capire cosa stiamo guardando
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
    st.info("👈 Apri la barra laterale per selezionare un Pilota/Moto.")

st.markdown("---")

# ==============================================================================
# 3. AREA DI LAVORO (WORKBENCH)
# ==============================================================================

# Se non ho selezionato nulla, non mostro i grafici per tenere pulito
if mezzo_sel and mezzo_sel != "Nuovo Mezzo...":
    
    # TAB PRINCIPALI
    tab_setup, tab_sim, tab_diario = st.tabs(["🔧 SETUP FISICO", "📈 SIMULATORE", "📝 DIARIO"])

    with tab_setup:
        st.caption("Configurazione Hardware Attuale")
        
        col_A, col_B = st.columns([1, 1])
        
        with col_A:
            st.subheader("Geometria")
            # SLIDER al posto di input manuali (Richiesta V7)
            d_clamp = st.slider("Clamp Ø (mm)", 8.0, 22.0, 12.0, step=0.5)
            d_pistone = st.number_input("Pistone Ø (mm)", value=50.0) # Questo cambia poco, va bene number
            
            # Pulsante AIUTO VISIVO
            with st.expander("❓ Guida Misure Pistone"):
                st.info("Misura la gola minima (d.thrt) e la larghezza porta (w.port).")
                # Qui metteremo l'immagine
                st.image("https://restackor.com/images/physics/flow-area/port-geometry.png", caption="Esempio Schema")

        with col_B:
            st.subheader("Molle & Precarichi")
            # Logica condizionale MOTO vs MTB
            if "MOTO" in mezzo_sel:
                k_molla = st.number_input("Molla (N/mm)", value=48.0, step=2.0)
                st.write(f"Rider Sag Target: ~{int(105)} mm")
            else:
                psi_main = st.number_input("Aria (PSI)", value=85, step=5)
                token = st.slider("Token/Spacer", 0, 5, 2)

    with tab_sim:
        st.subheader("Analisi Idraulica")
        
        # PRESET RAPIDI SPESSORI (Richiesta V7)
        st.write("Inserimento Rapido:")
        cols = st.columns(6)
        if cols[0].button("0.10"): st.session_state['last_shim'] = 0.10
        if cols[1].button("0.15"): st.session_state['last_shim'] = 0.15
        if cols[2].button("0.20"): st.session_state['last_shim'] = 0.20
        if cols[3].button("0.25"): st.session_state['last_shim'] = 0.25
        if cols[4].button("0.30"): st.session_state['last_shim'] = 0.30
        
        # Qui richiameremo la tua funzione di calcolo grafici
        st.line_chart([0, 10, 40, 80, 150, 250]) # Grafico Placeholder

    with tab_diario:
        st.subheader("Salva Sessione")
        f_pista = st.text_input("Pista / Luogo")
        f_feed = st.text_area("Feedback Pilota", placeholder="Es. Scalcia in frenata, affonda troppo...")
        
        if st.button("💾 SALVA LAVORO NEL CLOUD", type="primary"):
            # Qui chiameremo SuspensionDB.save_session(...)
            st.success("Dati salvati su Google Sheets!")
