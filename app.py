import streamlit as st
import pandas as pd
import numpy as np
import json
import time

# --- GESTIONE IMPORT DATABASE ---
try:
    from db_manager import SuspensionDB
except ImportError:
    st.error("⚠️ ERRORE CRITICO: Manca il file 'db_manager.py'.")
    st.stop()

# --- 1. CONFIGURAZIONE PAGINA & CSS ---
st.set_page_config(
    page_title="Suspension Lab V9", 
    page_icon="🔧", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZZATO (NUOVI COLORI) ---
st.markdown("""
<style>
    /* Stile Bottoni */
    div.stButton > button {
        height: 3em;
        font-weight: bold;
        width: 100%;
        border-radius: 6px;
        border: 1px solid #a0a0a0;
    }
    
    /* --- NUOVO COLORE BARRA LATERALE --- */
    [data-testid="stSidebar"] {
        background-color: #dce1e6; /* Grigio-Blu Tecnico più scuro */
        border-right: 2px solid #bcc4cc; /* Bordo di separazione */
    }
    
    /* Colore titoli per contrasto */
    h1, h2, h3 {
        color: #2c3e50;
    }
    
    /* Migliora leggibilità tab */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SISTEMA DI SICUREZZA (LOGIN) ---
PASSWORD_SEGRETA = "sospensioni2025" 

if "autenticato" not in st.session_state:
    st.session_state["autenticato"] = False

if not st.session_state["autenticato"]:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div style='background-color: #f0f2f6; padding: 30px; border-radius: 10px; border: 1px solid #ccc; text-align: center;'>
            <h2>🔒 Accesso Team</h2>
            <p>Inserisci la password per accedere al Suspension Lab</p>
        </div>
        """, unsafe_allow_html=True)
        input_pass = st.text_input("Password", type="password")
        if st.button("Accedi", type="primary"):
            if input_pass == PASSWORD_SEGRETA:
                st.session_state["autenticato"] = True
                st.rerun()
            else:
                st.error("Password Errata.")
    st.stop() 

# ==============================================================================
# 3. BARRA LATERALE: GESTIONE GARAGE
# ==============================================================================
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    st.markdown("---")
    
    # --- A. SELEZIONE PILOTA ---
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except Exception as e:
        st.error("Errore connessione DB")
        lista_piloti = []

    pilota_sel = st.selectbox("👤 SELEZIONA PILOTA", ["Seleziona..."] + lista_piloti)
    
    # --- B. SELEZIONE MEZZO ---
    mezzo_sel = None
    id_pilota_corrente = None
    
    if pilota_sel != "Seleziona..." and lista_piloti:
        try:
            id_pilota_corrente = pilota_sel.split("(")[-1].replace(")", "")
            lista_mezzi = SuspensionDB.get_mezzi_by_pilota(id_pilota_corrente)
            mezzo_sel = st.selectbox("🏍️ SELEZIONA MEZZO", ["Nuovo Mezzo..."] + lista_mezzi)
        except:
            st.error("Errore ID")

    st.markdown("---")
    
    # --- C. INSERIMENTO NUOVI DATI (FORM) ---
    st.subheader("➕ Gestione Rapida")

    # 1. FORM NUOVO PILOTA
    with st.expander("📝 Crea Nuovo Pilota"):
        with st.form("form_new_pilota"):
            n_nome = st.text_input("Nome e Cognome")
            n_peso = st.number_input("Peso (kg)", 40, 150, 75)
            n_liv = st.selectbox("Livello", ["Amatore", "Agonista", "Pro", "Hobby"])
            n_tel = st.text_input("Telefono")
            
            if st.form_submit_button("Salva Pilota"):
                if n_nome:
                    with st.spinner("Salvataggio..."):
                        SuspensionDB.add_pilota(n_nome, n_peso, n_liv, n_tel, "")
                        st.success("Salvato!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Manca il nome!")

    # 2. FORM NUOVO MEZZO
    if id_pilota_corrente:
        with st.expander("🏍️ Aggiungi Moto/Bici"):
            with st.form("form_new_mezzo"):
                st.caption(f"Proprietario: **{pilota_sel}**")
                m_tipo = st.selectbox("Tipo", ["MOTO", "MTB"])
                m_marca = st.text_input("Marca")
                m_mod = st.text_input("Modello")
                m_anno = st.number_input("Anno", 2000, 2026, 2024)
                m_fork = st.text_input("Forcella")
                m_mono = st.text_input("Mono")
                
                if st.form_submit_button("Salva Mezzo"):
                    if m_mod:
                        with st.spinner("Salvataggio..."):
                            SuspensionDB.add_mezzo(id_pilota_corrente, m_tipo, m_marca, m_mod, m_anno, m_fork, m_mono)
                            st.success("Mezzo aggiunto!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("Inserisci il modello!")
    else:
        st.info("Seleziona un pilota per aggiungere mezzi.")

# ==============================================================================
# 4. INTESTAZIONE DINAMICA
# ==============================================================================
if mezzo_sel and mezzo_sel != "Nuovo Mezzo...":
    nome_mezzo = mezzo_sel.split("(")[0]
    tipo_mezzo = "MOTO" if "MOTO" in mezzo_sel else "MTB"
    # Colori badge personalizzati
    badge_bg = "#2c3e50" if tipo_mezzo == "MOTO" else "#2980b9"
    
    st.markdown(f"""
    ## 🛠️ {nome_mezzo}
    <span style='background-color:{badge_bg}; padding:5px 10px; border-radius:5px; color:white; font-weight:bold; font-size:0.9em'>{tipo_mezzo}</span>
    """, unsafe_allow_html=True)

else:
    st.title("🛠️ Suspension Lab")
    st.info("👈 Inizia selezionando un Pilota dalla colonna grigia a sinistra.")
    st.stop()

st.markdown("---")

# ==============================================================================
# 5. AREA DI LAVORO
# ==============================================================================
tab_setup, tab_sim, tab_diario = st.tabs(["🔧 SETUP FISICO", "📈 SIMULATORE", "📝 DIARIO"])

# --- TAB 1: SETUP ---
with tab_setup:
    st.markdown("### ⚙️ Configurazione Hardware")
    colA, colB = st.columns(2)
    
    with colA:
        st.info("**Idraulica**")
        d_clamp = st.slider("Clamp Ø (mm)", 8.0, 24.0, 12.0, step=0.5)
        d_pistone = st.number_input("Pistone Ø (mm)", value=50.0)

    with colB:
        st.success("**Elastico**")
        if "MOTO" in mezzo_sel:
            k_molla = st.number_input("Molla (N/mm)", value=4.6, step=0.1)
            p_molla = st.number_input("Precarico (mm)", value=5.0, step=1.0)
        else:
            psi_main = st.number_input("Aria (PSI)", value=85, step=1)
            token = st.slider("Token", 0, 6, 2)

# --- TAB 2: SIMULATORE ---
with tab_sim:
    st.subheader("Analisi Idraulica")
    c1, c2 = st.columns([3, 1])
    with c1:
        # Grafico dimostrativo
        chart_data = pd.DataFrame(np.random.randn(20, 2), columns=['Forza', 'Velocità'])
        st.line_chart(chart_data)
    with c2:
        st.write("**Stack Compressione**")
        st.text("20 x 0.10\n18 x 0.10\n16 x 0.10")

# --- TAB 3: DIARIO ---
with tab_diario:
    st.subheader("Nuovo Report Test")
    
    with st.form("form_sessione"):
        c1, c2 = st.columns(2)
        f_pista = c1.text_input("📍 Pista / Luogo")
        f_cond = c2.selectbox("🌤️ Condizione", ["Secco", "Fango", "Sabbia", "Sassi", "Radici"])
        
        f_feed = st.text_area("💬 Feedback Pilota", height=100)
        f_rating = st.slider("⭐ Voto Setup", 1, 5, 3)
        
        dati_tecnici_snapshot = {"clamp": d_clamp, "pistone": d_pistone}
        
        if st.form_submit_button("💾 SALVA SESSIONE", type="primary"):
            if f_pista:
                try:
                    id_mezzo_clean = mezzo_sel.split("(")[-1].replace(")", "")
                    SuspensionDB.save_session(id_mezzo_clean, f_pista, f_cond, f_feed, f_rating, dati_tecnici_snapshot)
                    st.success("Sessione salvata!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Errore: {e}")
            else:
                st.warning("Scrivi almeno il nome della pista.")
