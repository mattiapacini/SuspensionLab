import streamlit as st
import pandas as pd
import numpy as np
import json
import time

# --- GESTIONE IMPORT DATABASE ---
# Se il file db_manager non esiste o ha errori, gestiamo il crash
try:
    from db_manager import SuspensionDB
except ImportError:
    st.error("⚠️ ERRORE CRITICO: Manca il file 'db_manager.py'.")
    st.info("Assicurati di aver creato il file db_manager.py con il codice aggiornato.")
    st.stop()

# --- 1. CONFIGURAZIONE PAGINA & CSS ---
st.set_page_config(
    page_title="Suspension Lab V8", 
    page_icon="🔧", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS per rendere l'app più bella e "toccabile" da mobile
st.markdown("""
<style>
    div.stButton > button {
        height: 3em;
        font-weight: bold;
        width: 100%;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] {
        background-color: #f4f5f7;
    }
    h1, h2, h3 {
        color: #31333F;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SISTEMA DI SICUREZZA (LOGIN) ---
PASSWORD_SEGRETA = "sospensioni2025"  # <--- CAMBIA QUESTA PASSWORD!

if "autenticato" not in st.session_state:
    st.session_state["autenticato"] = False

if not st.session_state["autenticato"]:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🔒 Suspension Lab")
        st.write("Area riservata al Team.")
        input_pass = st.text_input("Password", type="password")
        if st.button("Accedi", type="primary"):
            if input_pass == PASSWORD_SEGRETA:
                st.session_state["autenticato"] = True
                st.rerun()
            else:
                st.error("Password Errata.")
    st.stop() # Blocca l'esecuzione qui se non sei loggato

# ==============================================================================
# 3. BARRA LATERALE: GESTIONE GARAGE
# ==============================================================================
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    
    # --- A. SELEZIONE PILOTA ---
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except Exception as e:
        st.error("Errore connessione DB")
        lista_piloti = []

    pilota_sel = st.selectbox("👤 Pilota", ["Seleziona..."] + lista_piloti)
    
    # --- B. SELEZIONE MEZZO ---
    mezzo_sel = None
    id_pilota_corrente = None
    
    if pilota_sel != "Seleziona..." and lista_piloti:
        # Estrae l'ID tra parentesi: "Mario (P001)" -> "P001"
        try:
            id_pilota_corrente = pilota_sel.split("(")[-1].replace(")", "")
            lista_mezzi = SuspensionDB.get_mezzi_by_pilota(id_pilota_corrente)
            mezzo_sel = st.selectbox("🏍️ Mezzo", ["Nuovo Mezzo..."] + lista_mezzi)
        except:
            st.error("Errore lettura ID Pilota")

    st.markdown("---")
    
    # --- C. INSERIMENTO NUOVI DATI (FORM) ---
    st.subheader("➕ Gestione")

    # 1. FORM NUOVO PILOTA
    with st.expander("Aggiungi Pilota"):
        with st.form("form_new_pilota"):
            n_nome = st.text_input("Nome e Cognome")
            n_peso = st.number_input("Peso (kg)", 40, 150, 75)
            n_liv = st.selectbox("Livello", ["Amatore", "Agonista", "Pro", "Hobby"])
            n_tel = st.text_input("Telefono")
            
            if st.form_submit_button("Salva Pilota"):
                if n_nome:
                    with st.spinner("Salvataggio in corso..."):
                        res = SuspensionDB.add_pilota(n_nome, n_peso, n_liv, n_tel, "")
                        if res:
                            st.success("Fatto!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.warning("Inserisci almeno il nome.")

    # 2. FORM NUOVO MEZZO (Attivo solo se hai scelto un pilota)
    if id_pilota_corrente:
        with st.expander("Aggiungi Moto/Bici"):
            with st.form("form_new_mezzo"):
                st.write(f"Assegna a: **{pilota_sel}**")
                m_tipo = st.selectbox("Tipo", ["MOTO", "MTB"])
                m_marca = st.text_input("Marca (es. KTM)")
                m_mod = st.text_input("Modello (es. EXC 300)")
                m_anno = st.number_input("Anno", 2000, 2026, 2024)
                m_fork = st.text_input("Forcella (es. WP Xplor)")
                m_mono = st.text_input("Mono (es. WP Xplor)")
                
                if st.form_submit_button("Salva Mezzo"):
                    if m_mod:
                        with st.spinner("Salvataggio..."):
                            SuspensionDB.add_mezzo(id_pilota_corrente, m_tipo, m_marca, m_mod, m_anno, m_fork, m_mono)
                            st.success("Mezzo aggiunto!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("Inserisci almeno il modello.")
    else:
        st.info("Seleziona un pilota per aggiungere una moto.")

# ==============================================================================
# 4. INTESTAZIONE DINAMICA
# ==============================================================================
if mezzo_sel and mezzo_sel != "Nuovo Mezzo...":
    # Parsing stringa: "CRF 450 - MOTO (M001)"
    nome_mezzo = mezzo_sel.split("(")[0]
    tipo_mezzo = "MOTO" if "MOTO" in mezzo_sel else "MTB"
    badge_color = "#e6ffe6" if tipo_mezzo == "MOTO" else "#e6f7ff"
    text_color = "green" if tipo_mezzo == "MOTO" else "#0066cc"
    
    st.markdown(f"""
    ## 🛠️ {nome_mezzo}
    <span style='background-color:{badge_color}; padding:4px 8px; border-radius:4px; color:{text_color}; font-weight:bold; font-size:0.9em'>{tipo_mezzo}</span>
    """, unsafe_allow_html=True)

else:
    st.title("🛠️ Suspension Lab")
    st.info("👈 Inizia selezionando un Pilota dalla barra laterale.")
    st.markdown("---")
    st.stop() # Ferma il resto della pagina se non c'è una moto

st.markdown("---")

# ==============================================================================
# 5. AREA DI LAVORO (WORKBENCH)
# ==============================================================================

# Definiamo le TAB
tab_setup, tab_sim, tab_diario = st.tabs(["🔧 SETUP FISICO", "📈 SIMULATORE", "📝 DIARIO"])

# --- TAB 1: SETUP ---
with tab_setup:
    st.caption("Configurazione Hardware")
    colA, colB = st.columns(2)
    
    with colA:
        st.subheader("Geometria")
        d_clamp = st.slider("Clamp Ø (mm)", 8.0, 24.0, 12.0, step=0.5, help="Diametro del pacco lamellare al centro")
        d_pistone = st.number_input("Pistone Ø (mm)", value=50.0)
        
        with st.expander("❓ Guida Misure Pistone"):
            st.info("Misura la gola minima (d.thrt) e la larghezza porta (w.port).")
            # Link immagine placeholder
            st.image("https://restackor.com/images/physics/flow-area/port-geometry.png", caption="Riferimento")

    with colB:
        st.subheader("Elemento Elastico")
        # Logica diversa per Moto o MTB
        if "MOTO" in mezzo_sel:
            k_molla = st.number_input("Molla Forcella (N/mm)", value=4.6, step=0.1)
            p_molla = st.number_input("Precarico Molla (mm)", value=5.0, step=1.0)
            st.info("Target Sag consigliato: 35-40mm (Statico)")
        else:
            psi_main = st.number_input("Pressione Aria (PSI)", value=85, step=1)
            token = st.slider("Token / Spacers", 0, 6, 2)
            st.info("Target Sag consigliato: 20-25%")

# --- TAB 2: SIMULATORE ---
with tab_sim:
    st.subheader("Analisi Idraulica")
    st.write("Configurazione Pacco Lamellare (Compressione)")
    
    # Pulsanti rapidi per inserimento (Placeholder logica futura)
    cols = st.columns(6)
    shims = [0.10, 0.15, 0.20, 0.25, 0.30]
    
    if "stack" not in st.session_state: st.session_state["stack"] = []
    
    for i, s in enumerate(shims):
        if cols[i].button(f"+ {s}"):
            st.session_state["stack"].append(s)
            
    if cols[-1].button("Reset"):
        st.session_state["stack"] = []
        
    st.write(f"Stack attuale: {st.session_state['stack']}")

    # Grafico dimostrativo
    chart_data = pd.DataFrame(
        np.random.randn(20, 2),
        columns=['Forza (N)', 'Velocità (m/s)'])
    st.line_chart(chart_data)

# --- TAB 3: DIARIO ---
with tab_diario:
    st.subheader("Nuova Sessione di Test")
    
    with st.form("form_sessione"):
        c1, c2 = st.columns(2)
        f_pista = c1.text_input("Pista / Luogo")
        f_cond = c2.selectbox("Condizione", ["Secco", "Fango", "Sabbia", "Sassi", "Radici"])
        
        f_feed = st.text_area("Feedback Pilota", placeholder="Es. La moto scalcia sulle buche in frenata...")
        f_rating = st.slider("Voto al Setup", 1, 5, 3)
        
        # Simuliamo i dati tecnici attuali da salvare
        dati_tecnici_snapshot = {
            "clamp": d_clamp,
            "pistone": d_pistone,
            "stack": st.session_state.get("stack", [])
        }
        
        submit_session = st.form_submit_button("💾 SALVA NEL DATABASE")
        
        if submit_session:
            if f_pista:
                try:
                    # Pulizia ID Mezzo: "CRF (M001)" -> "M001"
                    id_mezzo_clean = mezzo_sel.split("(")[-1].replace(")", "")
                    
                    SuspensionDB.save_session(
                        id_mezzo_clean, 
                        f_pista, 
                        f_cond, 
                        f_feed, 
                        f_rating, 
                        dati_tecnici_snapshot
                    )
                    st.success("Sessione salvata con successo su Google Sheets!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Errore Salvataggio: {e}")
            else:
                st.warning("Inserisci almeno il nome della pista.")
