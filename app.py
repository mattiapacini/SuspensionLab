import streamlit as st
import subprocess
import sys
import time

# --- 1. SISTEMA DI AUTO-INSTALLAZIONE (FIX PER ERRORI LIBRERIE) ---
# Se il server non trova matplotlib o gsheets, li installiamo al volo qui.
def install_and_import(package_name, import_name=None):
    if import_name is None: import_name = package_name
    try:
        __import__(import_name)
    except ImportError:
        warning_placeholder = st.empty()
        warning_placeholder.warning(f"⚙️ Installazione di {package_name} in corso... Attendi...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            warning_placeholder.success(f"✅ {package_name} installato! Riavvio...")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Errore installazione {package_name}: {e}")
            st.stop()

# Verifichiamo le librerie critiche
install_and_import("matplotlib")
install_and_import("streamlit-gsheets")

# --- 2. IMPORTAZIONI REALI ---
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from streamlit_gsheets import GSheetsConnection

# Import moduli locali (devono esistere nella cartella!)
try:
    from db_manager import SuspensionDB
    from physics import SuspensionPhysics
except ImportError:
    st.error("⚠️ MANCANO I FILE: Assicurati che 'db_manager.py' e 'physics.py' siano nella stessa cartella.")
    st.stop()

# --- 3. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="SuspensionLab",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 4. STILE CSS (DARK SIDEBAR) ---
st.markdown("""
<style>
    /* Sidebar Scura Professionale */
    [data-testid="stSidebar"] {
        background-color: #1a1c24;
        border-right: 1px solid #333;
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    /* Bottoni Sidebar */
    [data-testid="stSidebar"] button {
        background-color: #2b303b;
        color: white;
        border: 1px solid #4a4e59;
        transition: 0.3s;
    }
    [data-testid="stSidebar"] button:hover {
        border-color: #00ace6;
        color: #00ace6;
        background-color: #333842;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.05rem;
        font-weight: 600;
        color: #1a1c24;
    }
    /* Titoli */
    h1, h2, h3 { color: #1a1c24; }
</style>
""", unsafe_allow_html=True)

# --- 5. FUNZIONE GRAFICO VISUALIZER (MATPLOTLIB) ---
def plot_shim_bending(k_factor, stack, d_clamp, d_piston, geo_data):
    if not stack: return None
    
    # Parametri grafici
    max_od = max([float(x['od']) for x in stack])
    speeds = [0.5, 2.0, 6.0] # Velocità simulat
    colors = ['#27ae60', '#f39c12', '#c0392b'] # Verde, Giallo, Rosso
    
    # Simulazione rapida per ottenere i lift
    df_sim = SuspensionPhysics.simulate_damping_curve(k_factor, geo_data)
    
    fig, ax = plt.subplots(figsize=(8, 3.5))
    
    r_clamp = d_clamp / 2.0
    r_piston = d_piston / 2.0
    r_port = geo_data['r_port']
    
    # Disegno Componenti Fissi
    ax.plot([0, r_piston], [0, 0], color='#2c3e50', linewidth=3, label='Pistone') 
    ax.fill_between([0, r_clamp], [0, 0], [0.5, 0.5], color='#34495e', label='Clamp')
    ax.axvline(x=r_port, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.text(r_port, -0.4, 'Port', ha='center', fontsize=8, color='gray')

    # Disegno Curve Lamelle
    for i, v_target in enumerate(speeds):
        # Trova la riga più vicina alla velocità target
        row = df_sim.iloc[(df_sim['Velocità (m/s)'] - v_target).abs().argsort()[:1]]
        y_max = row['Lift (mm)'].values[0]
        
        # Calcola la forma
        radii, deflections = SuspensionPhysics.get_shim_profile(k_factor, d_clamp, max_od, y_max)
        
        ax.plot(radii, deflections, color=colors[i], linewidth=2, label=f'{v_target} m/s')
        ax.fill_between(radii, deflections, 0, color=colors[i], alpha=0.1)

    ax.set_title("Visualizzazione Flessione Reale", fontsize=10, fontweight='bold', color='#333')
    ax.set_ylim(-0.5, 3.0)
    ax.set_xlim(0, r_piston + 2)
    ax.legend(loc='upper left', fontsize=8, frameon=True)
    ax.grid(True, linestyle=':', alpha=0.5)
    plt.tight_layout()
    return fig

# --- 6. SISTEMA LOGIN ---
PASSWORD_SEGRETA = "sospensioni2025" 

if "autenticato" not in st.session_state: st.session_state["autenticato"] = False

if not st.session_state["autenticato"]:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("🔒 Accesso Riservato")
        input_pass = st.text_input("Inserisci Password", type="password")
        if st.button("ENTRA", type="primary", use_container_width=True):
            if input_pass == PASSWORD_SEGRETA:
                st.session_state["autenticato"] = True
                st.rerun()
            else:
                st.error("Password Errata.")
    st.stop() 

# --- 7. SIDEBAR & GESTIONE DATI ---
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    st.markdown("---")
    
    # Caricamento Piloti
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except Exception as e:
        st.error(f"Err DB: {e}")
        lista_piloti = []

    pilota_sel = st.selectbox("👤 PILOTA", ["Seleziona..."] + lista_piloti)
    
    # Caricamento Mezzi
    mezzo_sel = None
    id_pilota_corrente = None
    
    if pilota_sel != "Seleziona..." and lista_piloti:
        id_pilota_corrente = pilota_sel.split("(")[-1].replace(")", "")
        lista_mezzi = SuspensionDB.get_mezzi_by_pilota(id_pilota_corrente)
        mezzo_sel = st.selectbox("🏍️ MEZZO", ["Nuovo Mezzo..."] + lista_mezzi)

    st.markdown("---")
    st.subheader("➕ Gestione")

    # Form Nuovo Pilota
    with st.expander("📝 Nuovo Pilota"):
        with st.form("new_p"):
            n_nome = st.text_input("Nome")
            n_peso = st.number_input("Peso", 40, 150, 75)
            n_liv = st.selectbox("Livello", ["Amatore", "Agonista", "Pro"])
            if st.form_submit_button("Salva"):
                if n_nome:
                    SuspensionDB.add_pilota(n_nome, n_peso, n_liv, "", "")
                    st.success("Ok!")
                    time.sleep(1)
                    st.rerun()

    # Form Nuovo Mezzo
    if id_pilota_corrente:
        with st.expander("🏍️ Nuovo Mezzo"):
            with st.form("new_m"):
                st.write(f"Per: **{pilota_sel.split('(')[0]}**")
                m_tipo = st.selectbox("Tipo", ["MOTO", "MTB"])
                m_marca = st.text_input("Marca")
                m_mod = st.text_input("Modello")
                m_anno = st.number_input("Anno", 2000, 2030, 2024)
                if st.form_submit_button("Salva"):
                    if m_mod:
                        SuspensionDB.add_mezzo(id_pilota_corrente, m_tipo, m_marca, m_mod, m_anno, "", "")
                        st.success("Ok!")
                        time.sleep(1)
                        st.rerun()

# --- 8. INTERFACCIA PRINCIPALE ---
if mezzo_sel and mezzo_sel != "Nuovo Mezzo...":
    nome_mezzo = mezzo_sel.split("(")[0]
    badge_col = "#2ecc71" if "MOTO" in mezzo_sel else "#e67e22"
    
    st.markdown(f"""
    ## 🛠️ {nome_mezzo} <span style='font-size:0.6em; background-color:{badge_col}; color:white; padding:4px 8px; border-radius:5px; vertical-align:middle'>{mezzo_sel.split('-')[1].strip().split(' ')[0]}</span>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    tab_setup, tab_sim, tab_diario, tab_history = st.tabs(["🔧 SETUP", "🧪 SIMULATORE", "📝 DIARIO", "🗃️ STORICO"])

    # --- TAB SETUP ---
    with tab_setup:
        c1, c2 = st.columns(2)
        with c1:
            st.info("**Hardware Base**")
            st.number_input("Clamp Ø (mm)", 8.0, 24.0, 12.0)
            st.number_input("Pistone Ø (mm)", value=50.0)
        with c2:
            st.success("**Setting Attuale**")
            if "MOTO" in mezzo_sel:
                st.number_input("K Molla", 4.0, 10.0, 4.8)
                st.slider("Comp (Click)", 0, 25, 12)
                st.slider("Reb (Click)", 0, 25, 12)
            else:
                st.number_input("Aria (PSI)", 50, 300, 85)

    # --- TAB SIMULATORE (CUORE DEL SISTEMA) ---
    with tab_sim:
        st.subheader("Analisi Idraulica & Flessione")
        
        col_geo, col_stack, col_res = st.columns([1, 1.2, 2])
        
        # A. INPUT GEOMETRIA
        with col_geo:
            st.markdown("##### 1. Valvola")
            with st.container(border=True):
                sim_d_piston = st.number_input("Ø Pistone", value=50.0, key="dp")
                sim_r_port = st.number_input("r.port (Leva)", value=12.0, help="Distanza centro-passaggi")
                sim_w_port = st.number_input("w.port (Largh)", value=8.0)
                sim_n_ports = st.number_input("N° Port", value=4)
            
            geo_data = {
                "d_piston": sim_d_piston, "d_rod": 16.0, 
                "r_port": sim_r_port, "w_port": sim_w_port, "n_ports": sim_n_ports
            }

        # B. INPUT STACK
        with col_stack:
            st.markdown("##### 2. Stack")
            with st.container(border=True):
                sim_d_clamp = st.number_input("Ø Clamp", value=12.0, key="dc")
                
                if "sim_stack" not in st.session_state: st.session_state["sim_stack"] = []
                
                # Input riga singola
                cc1, cc2, cc3 = st.columns([0.8, 1, 1])
                qty = cc1.number_input("Qt", 1, 10, 1)
                od = cc2.number_input("Ø", 6.0, 44.0, 30.0, step=1.0)
                th = cc3.selectbox("Th", [0.10, 0.15, 0.20, 0.25, 0.30])
                
                if st.button("⬇️ Aggiungi", use_container_width=True):
                    st.session_state["sim_stack"].append({"qty": qty, "od": od, "th": th})
                
                # Tabella Stack
                if st.session_state["sim_stack"]:
                    st.dataframe(pd.DataFrame(st.session_state["sim_stack"]), hide_index=True, use_container_width=True)
                    if st.button("🗑️ Reset", use_container_width=True):
                        st.session_state["sim_stack"] = []
                        st.rerun()

        # C. OUTPUT
        with col_res:
            st.markdown("##### 3. Risultati")
            if st.button("🔥 CALCOLA ANALISI", type="primary", use_container_width=True):
                if st.session_state["sim_stack"]:
                    # Calcoli Fisici
                    k_factor = SuspensionPhysics.calculate_stiffness_factor(
                        st.session_state["sim_stack"], sim_d_clamp, sim_d_piston
                    )
                    df_res = SuspensionPhysics.simulate_damping_curve(k_factor, geo_data)
                    
                    # Metriche
                    m1, m2 = st.columns(2)
                    m1.metric("Rigidezza (K)", f"{k_factor:.1f}")
                    m2.metric("Forza Max", f"{df_res['Forza (N)'].max():.0f} N")
                    
                    # Grafici
                    t1, t2 = st.tabs(["📐 Visualizer Flessione", "📈 Curva Damping"])
                    
                    with t1:
                        fig = plot_shim_bending(k_factor, st.session_state["sim_stack"], sim_d_clamp, sim_d_piston, geo_data)
                        st.pyplot(fig)
                        st.caption("Il grafico mostra la deformazione reale delle lamelle a diverse velocità.")
                    
                    with t2:
                        st.line_chart(df_res.set_index("Velocità (m/s)")["Forza (N)"])
                else:
                    st.warning("Aggiungi almeno una lamella per calcolare.")

    # --- TAB DIARIO ---
    with tab_diario:
        st.subheader("Report Sessione")
        with st.form("diario_form"):
            c1, c2 = st.columns(2)
            f_pista = c1.text_input("📍 Pista / Luogo")
            f_cond = c2.selectbox("🌤️ Condizione", ["Secco", "Fango", "Sabbia", "Sassi", "Misto"])
            f_feed = st.text_area("💬 Feedback Pilota")
            f_rating = st.slider("⭐ Voto Generale", 1, 5, 3)
            
            # Snapshot dati tecnici attuali
            snapshot = {
                "stack": st.session_state.get("sim_stack", []),
                "geo": geo_data if 'geo_data' in locals() else {}
            }
            
            if st.form_submit_button("💾 ARCHIVIA SESSIONE", type="primary"):
                if f_pista:
                    id_m = mezzo_sel.split("(")[-1].replace(")", "")
                    SuspensionDB.save_session(id_m, f_pista, f_cond, f_feed, f_rating, snapshot)
                    st.success("Sessione Salvata!")
                    time.sleep(1)
                    st.rerun()

    # --- TAB STORICO ---
    with tab_history:
        st.subheader("Storico Sessioni")
        id_m = mezzo_sel.split("(")[-1].replace(")", "")
        df_hist = SuspensionDB.get_history_by_mezzo(id_m)
        
        if df_hist.empty:
            st.info("Nessuna sessione trovata per questo mezzo.")
        else:
            for _, row in df_hist.iterrows():
                with st.expander(f"📅 {row['data']} - {row['pista_luogo']} (Voto: {row['rating']})"):
                    st.write(f"**Condizione:** {row['condizione']}")
                    st.write(f"**Feedback:** {row['feedback_text']}")
                    try:
                        dati = json.loads(row['dati_tecnici_json'])
                        st.caption("Dati tecnici salvati:")
                        st.json(dati)
                    except:
                        st.caption("Nessun dato tecnico allegato.")

else:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.info("👈 Seleziona un Pilota dal menu laterale per iniziare.")
