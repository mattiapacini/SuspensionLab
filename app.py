import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import time

# --- IMPORT MODULI ---
try:
    from db_manager import SuspensionDB
    from physics import SuspensionPhysics
except ImportError:
    st.error("⚠️ ERRORE: Assicurati che db_manager.py e physics.py siano presenti.")
    st.stop()

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="SuspensionLab Pro",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS DARK & STYLE ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1a1c24; border-right: 1px solid #333; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #2b303b !important; color: white !important; border: 1px solid #4a4e59 !important;
    }
    h1, h2, h3 { color: #1a1c24; }
    .stButton>button { border-radius: 5px; font-weight: 600; }
    /* Fix per metriche e testi */
    p, label { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONE GRAFICA ---
def plot_shim_bending(k_factor, stack, d_clamp, d_piston, geo_data):
    if not stack: return None
    max_od = max([float(x['od']) for x in stack])
    speeds = [0.5, 2.0, 6.0]
    colors = ['#2ecc71', '#f1c40f', '#e74c3c']
    
    df_sim = SuspensionPhysics.simulate_damping_curve(k_factor, geo_data)
    fig, ax = plt.subplots(figsize=(8, 3.5))
    
    r_clamp = d_clamp / 2.0
    r_piston = d_piston / 2.0
    r_port = geo_data['r_port']
    
    ax.plot([0, r_piston], [0, 0], color='#2c3e50', linewidth=4, label='Pistone') 
    ax.fill_between([0, r_clamp], [0, 0], [0.5, 0.5], color='#34495e', label='Clamp')
    ax.axvline(x=r_port, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    for i, v in enumerate(speeds):
        row = df_sim.iloc[(df_sim['Velocità (m/s)'] - v).abs().argsort()[:1]]
        y_max = row['Lift (mm)'].values[0]
        radii, deflections = SuspensionPhysics.get_shim_profile(k_factor, d_clamp, max_od, y_max)
        ax.plot(radii, deflections, color=colors[i], linewidth=2, label=f'{v} m/s')
        ax.fill_between(radii, deflections, 0, color=colors[i], alpha=0.1)

    ax.set_title("Visualizzazione Flessione Reale", fontsize=10)
    ax.set_ylim(-0.5, 3.0)
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, linestyle=':', alpha=0.3)
    return fig

# --- LOGIN ---
if "autenticato" not in st.session_state: st.session_state["autenticato"] = False
if not st.session_state["autenticato"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("🔒 Accesso Riservato")
        if st.text_input("Password", type="password") == "sospensioni2025":
            if st.button("ENTRA", type="primary", use_container_width=True):
                st.session_state["autenticato"] = True
                st.rerun()
    st.stop() 

# --- SIDEBAR ---
with st.sidebar:
    st.title("🗂️ NAVIGATORE")
    st.markdown("---")
    
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except:
        lista_piloti = []

    pilota_sel = st.selectbox("👤 PILOTA", ["Seleziona..."] + lista_piloti)
    
    mezzo_sel_full = None
    id_pilota_corrente = None
    id_mezzo_corrente = None
    
    if pilota_sel != "Seleziona..." and lista_piloti:
        id_pilota_corrente = pilota_sel.split("(")[-1].replace(")", "")
        lista_mezzi = SuspensionDB.get_mezzi_by_pilota(id_pilota_corrente)
        
        mezzo_sel_full = st.selectbox("🏍️ MEZZO", ["Nuovo Mezzo..."] + lista_mezzi)
        
        # Estraiamo il vero ID_MEZZO dalla stringa
        if mezzo_sel_full and "#" in mezzo_sel_full:
            id_mezzo_corrente = mezzo_sel_full.split("#")[-1]

    st.markdown("---")
    
    # FORM AGGIUNTA PILOTA
    with st.expander("➕ Nuovo Pilota"):
        with st.form("new_p", clear_on_submit=True):
            n_nome = st.text_input("Nome Cognome")
            n_tel = st.text_input("Telefono")
            n_peso = st.number_input("Peso", 40, 150, 75)
            n_liv = st.selectbox("Livello", ["Amatore", "Agonista", "Pro"])
            n_note = st.text_area("Note")
            if st.form_submit_button("Salva"):
                if n_nome:
                    SuspensionDB.add_pilota(n_nome, n_peso, n_liv, n_tel, n_note)
                    st.success("Ok")
                    time.sleep(1)
                    st.rerun()

    # FORM AGGIUNTA MEZZO
    if id_pilota_corrente:
        with st.expander("➕ Aggiungi Moto"):
            with st.form("new_m", clear_on_submit=True):
                st.write(f"Per: **{pilota_sel.split('(')[0]}**")
                m_tipo = st.selectbox("Tipo", ["MOTO", "MTB"])
                m_marca = st.text_input("Marca")
                m_mod = st.text_input("Modello")
                m_anno = st.number_input("Anno", 2000, 2030, 2024)
                m_fork = st.text_input("Modello Forcella")
                m_mono = st.text_input("Modello Mono")
                
                if st.form_submit_button("Salva Moto"):
                    if m_mod:
                        SuspensionDB.add_mezzo(id_pilota_corrente, m_tipo, m_marca, m_mod, m_anno, m_fork, m_mono)
                        st.success("Moto aggiunta in Garage!")
                        time.sleep(1)
                        st.rerun()

# --- MAIN PAGE ---
if id_mezzo_corrente:
    nome_mezzo_display = mezzo_sel_full.split("#")[0]
    st.markdown(f"## 🛠️ {nome_mezzo_display} <span style='font-size:0.6em; color:gray'>Workspace</span>", unsafe_allow_html=True)
    st.markdown("---")

    tab_setup, tab_sim, tab_diario, tab_history = st.tabs(["🔧 SETUP", "🧪 SIMULATORE", "📝 DIARIO", "🗃️ STORICO"])

    # --- TAB SETUP (FIXED KEYS PER EVITARE CRASH) ---
    with tab_setup:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info("Forcella")
            # Aggiunte le keys univoche per evitare DuplicateElementId
            st.number_input("Molla (N/mm)", 0.0, 20.0, 4.6, step=0.1, key="k_fork_val") 
            st.slider("Comp", 0, 30, 12, key="comp_fork_val")
            st.slider("Reb", 0, 30, 12, key="reb_fork_val")
        with c2:
            st.warning("Mono")
            st.number_input("Molla (N/mm)", 0.0, 150.0, 54.0, step=1.0, key="k_shock_val")
            st.slider("Comp H", 0, 30, 10, key="comph_shock_val")
            st.slider("Reb", 0, 30, 12, key="reb_shock_val")
        with c3:
            st.success("Note")
            st.text_area("Note Setup Attuale", height=150, key="note_setup_general")

    # --- TAB SIMULATORE ---
    with tab_sim:
        st.subheader("Analisi Idraulica")
        c_geo, c_stack, c_res = st.columns([1, 1.2, 2])
        
        with c_geo:
            with st.container(border=True):
                st.markdown("**Valvola**")
                geo_data = {
                    "d_piston": st.number_input("Ø Pistone", value=50.0, key="sim_dp"),
                    "d_rod": 16.0,
                    "r_port": st.number_input("r.port", value=12.0, key="sim_rp"),
                    "w_port": 8.0, "n_ports": 4
                }

        with c_stack:
            with st.container(border=True):
                st.markdown("**Stack**")
                sim_d_clamp = st.number_input("Ø Clamp", value=12.0, key="sim_dc")
                if "sim_stack" not in st.session_state: st.session_state["sim_stack"] = []
                
                cc1, cc2, cc3 = st.columns([0.8, 1, 1])
                qty = cc1.number_input("Q", 1, 10, 1, key="add_q")
                od = cc2.number_input("OD", 6.0, 44.0, 30.0, key="add_od")
                th = cc3.selectbox("Th", [0.10, 0.15, 0.20, 0.25, 0.30], key="add_th")
                
                if st.button("⬇️ Add", key="btn_add"):
                    st.session_state["sim_stack"].append({"qty": qty, "od": od, "th": th})
                
                if st.session_state["sim_stack"]:
                    st.dataframe(pd.DataFrame(st.session_state["sim_stack"]), hide_index=True)
                    if st.button("🗑️ Reset", key="btn_rst"): 
                        st.session_state["sim_stack"] = []
                        st.rerun()

        with c_res:
            if st.button("🔥 CALCOLA", type="primary", use_container_width=True, key="btn_calc"):
                if st.session_state["sim_stack"]:
                    k = SuspensionPhysics.calculate_stiffness_factor(st.session_state["sim_stack"], sim_d_clamp, geo_data["d_piston"])
                    df_res = SuspensionPhysics.simulate_damping_curve(k, geo_data)
                    
                    st.pyplot(plot_shim_bending(k, st.session_state["sim_stack"], sim_d_clamp, geo_data["d_piston"], geo_data))
                    st.line_chart(df_res.set_index("Velocità (m/s)")["Forza (N)"])

    # --- TAB DIARIO ---
    with tab_diario:
        st.subheader("Report Sessione")
        with st.form("diario_form"):
            c1, c2 = st.columns(2)
            f_pista = c1.text_input("📍 Pista / Luogo")
            f_cond = c2.selectbox("🌤️ Condizione", ["Secco", "Fango", "Sabbia", "Misto"])
            f_feed = st.text_area("💬 Feedback")
            f_rating = st.slider("⭐ Voto", 1, 5, 3)
            
            snapshot = {"stack": st.session_state.get("sim_stack", []), "geo": geo_data}
            
            if st.form_submit_button("💾 SALVA SESSIONE", type="primary"):
                if f_pista:
                    SuspensionDB.save_session(id_mezzo_corrente, f_pista, f_cond, f_feed, f_rating, snapshot)
                    st.success("Salvato!")
                    time.sleep(1)
                    st.rerun()

    # --- TAB STORICO ---
    with tab_history:
        st.subheader("Storico")
        df_hist = SuspensionDB.get_history_by_mezzo(id_mezzo_corrente)
        if not df_hist.empty:
            for _, row in df_hist.iterrows():
                with st.expander(f"📅 {row['data']} - {row['pista_luogo']} (Voto: {row['rating']})"):
                    st.write(f"**Condizione:** {row['condizione']}")
                    st.write(f"**Feedback:** {row['feedback_text']}")
                    try:
                        dati = json.loads(row['dati_tecnici_json'])
                        if dati.get('stack'):
                            st.caption("Stack usato:")
                            st.dataframe(pd.DataFrame(dati['stack']), hide_index=True)
                    except:
                        pass
        else:
            st.info("Nessuna sessione.")

else:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("👈 Seleziona un Pilota e una Moto per iniziare.")
