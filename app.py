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
    page_title="Suspension Lab", 
    page_icon="🔧", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZZATO (DARK MODE SIDEBAR) ---
st.markdown("""
<style>
    /* Sidebar Scura */
    [data-testid="stSidebar"] {
        background-color: #1a1c24;
        border-right: 1px solid #333;
    }
    /* Testi Sidebar Bianchi */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p {
        color: #ffffff !important;
    }
    /* Bottoni Sidebar */
    [data-testid="stSidebar"] button {
        background-color: #2b303b;
        color: white;
        border: 1px solid #4a4e59;
    }
    [data-testid="stSidebar"] button:hover {
        border-color: #00ace6;
        color: #00ace6;
    }
    /* Titoli Pagina */
    h1, h2, h3 { color: #1a1c24; }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. LOGIN (SICUREZZA) ---
PASSWORD_SEGRETA = "sospensioni2025" 

if "autenticato" not in st.session_state:
    st.session_state["autenticato"] = False

if not st.session_state["autenticato"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div style='background-color: #f0f2f6; padding: 40px; border-radius: 12px; border: 1px solid #ccc; text-align: center;'>
            <h2 style='color:#333'>🔒 Accesso Team</h2>
            <p style='color:#666'>Inserisci la password di sicurezza</p>
        </div><br>""", unsafe_allow_html=True)
        input_pass = st.text_input("Password", type="password")
        if st.button("ACCEDI AL LAB", type="primary"):
            if input_pass == PASSWORD_SEGRETA:
                st.session_state["autenticato"] = True
                st.rerun()
            else:
                st.error("Password Errata.")
    st.stop() 

# ==============================================================================
# 3. BARRA LATERALE: GESTIONE ARCHIVIO
# ==============================================================================
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    st.markdown("---")
    
    # --- SELEZIONE PILOTA ---
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except Exception as e:
        st.error("Errore DB")
        lista_piloti = []

    pilota_sel = st.selectbox("👤 SELEZIONA PILOTA", ["Seleziona..."] + lista_piloti)
    
    # --- SELEZIONE MEZZO ---
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
    
    # --- INSERIMENTO NUOVI DATI ---
    st.subheader("➕ Gestione")

    # NUOVO PILOTA
    with st.expander("📝 Nuovo Pilota"):
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

    # NUOVO MEZZO
    if id_pilota_corrente:
        with st.expander("🏍️ Nuovo Mezzo"):
            with st.form("form_new_mezzo"):
                st.write(f"Proprietario: **{pilota_sel.split('(')[0]}**")
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

# ==============================================================================
# 4. INTESTAZIONE & WORKBENCH
# ==============================================================================
if mezzo_sel and mezzo_sel != "Nuovo Mezzo...":
    nome_mezzo = mezzo_sel.split("(")[0]
    tipo_mezzo = "MOTO" if "MOTO" in mezzo_sel else "MTB"
    badge_bg = "#1a1c24" 
    
    st.markdown(f"""
    ## 🛠️ {nome_mezzo}
    <span style='background-color:{badge_bg}; padding:6px 12px; border-radius:6px; color:white; font-weight:bold; font-size:0.9em; letter-spacing: 1px;'>{tipo_mezzo}</span>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    # --- DEFINIZIONE TABS (AGGIUNTO "STORICO") ---
    tab_setup, tab_sim, tab_diario, tab_history = st.tabs(["🔧 SETUP", "📈 SIMULATORE", "📝 DIARIO", "🗃️ STORICO"])

    # --- TAB 1: SETUP FISICO ---
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
            chart_data = pd.DataFrame(np.random.randn(20, 2), columns=['Forza', 'Velocità'])
            st.line_chart(chart_data)
        with c2:
            st.write("**Stack Compressione**")
            st.code("20 x 0.10\n18 x 0.10\n16 x 0.10", language="text")

    # --- TAB 3: DIARIO (NUOVA SESSIONE) ---
    with tab_diario:
        st.subheader("Nuovo Report Test")
        with st.form("form_sessione"):
            c1, c2 = st.columns(2)
            f_pista = c1.text_input("📍 Pista / Luogo")
            f_cond = c2.selectbox("🌤️ Condizione", ["Secco", "Fango", "Sabbia", "Sassi", "Radici"])
            f_feed = st.text_area("💬 Feedback Pilota", height=100)
            f_rating = st.slider("⭐ Voto Setup", 1, 5, 3)
            
            # Snapshot dei dati attuali
            dati_tecnici_snapshot = {
                "clamp": d_clamp, 
                "pistone": d_pistone,
                "molla": k_molla if "MOTO" in mezzo_sel else psi_main
            }
            
            if st.form_submit_button("💾 SALVA SESSIONE", type="primary"):
                if f_pista:
                    try:
                        id_mezzo_clean = mezzo_sel.split("(")[-1].replace(")", "")
                        SuspensionDB.save_session(id_mezzo_clean, f_pista, f_cond, f_feed, f_rating, dati_tecnici_snapshot)
                        st.success("Sessione salvata nello storico!")
                        time.sleep(1)
                        st.rerun() # Ricarica per mostrare subito nel tab Storico
                    except Exception as e:
                        st.error(f"Errore: {e}")
                else:
                    st.warning("Scrivi almeno il nome della pista.")

    # --- TAB 4: STORICO (NOVITÀ) ---
    with tab_history:
        st.subheader(f"🗂️ Storico Interventi: {nome_mezzo}")
        
        try:
            id_mezzo_clean = mezzo_sel.split("(")[-1].replace(")", "")
            df_storico = SuspensionDB.get_history_by_mezzo(id_mezzo_clean)
            
            if df_storico.empty:
                st.info("Nessuna sessione registrata per questo mezzo.")
            else:
                # Mostra tabella sintetica
                st.dataframe(
                    df_storico[['data', 'pista_luogo', 'condizione', 'rating', 'feedback_text']],
                    use_container_width=True,
                    hide_index=True
                )
                st.markdown("---")
                st.write("🔍 **Dettagli Sessioni:**")
                
                # Cards dettagliate
                for index, row in df_storico.iterrows():
                    with st.expander(f"📅 {row['data']} - {row['pista_luogo']} (Voto: {row['rating']}/5)"):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(f"**Feedback:**\n_{row['feedback_text']}_")
                            st.markdown(f"**Condizione:** {row['condizione']}")
                        with c2:
                            st.caption("🔧 Setup usato:")
                            try:
                                dati = json.loads(row['dati_tecnici_json'])
                                st.json(dati)
                            except:
                                st.error("Dati non leggibili")
        except Exception as e:
            st.error(f"Errore caricamento storico: {e}")

else:
    st.title("🛠️ Suspension Lab")
    st.info("👈 Inizia selezionando un Pilota dal menu scuro a sinistra.")
