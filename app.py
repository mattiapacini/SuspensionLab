import streamlit as st
import subprocess
import sys

# --- HACK: INSTALLAZIONE FORZATA ---
# Se Streamlit ignora requirements.txt, lo obblighiamo a installare qui.
try:
    import matplotlib
except ImportError:
    st.toast("🔧 Installazione forzata di Matplotlib in corso...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"])
    import matplotlib

# Ora importiamo il resto normalmente
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
# -----------------------------------

# ... qui sotto continua il tuo codice normale ...

# --- BLOCCO DI SICUREZZA PER MATPLOTLIB ---
try:
    import matplotlib.pyplot as plt
    has_matplotlib = True
except Exception as e:
    has_matplotlib = False
    # Non mostriamo l'errore subito per non bloccare l'app
# ------------------------------------------

# Se usi gsheets, proteggi anche lui per ora:
try:
    from streamlit_gsheets import GSheetsConnection
except:
    pass
# --- IMPORT MODULI ---
try:
    from db_manager import SuspensionDB
    from physics import SuspensionPhysics
except ImportError:
    st.error("⚠️ ERRORE: Carica prima db_manager.py e physics.py")
    st.stop()

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="SuspensionLab", 
    page_icon="🔧", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS STILE PRO (Sidebar Scura) ---
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: #1a1c24;
        border-right: 1px solid #333;
    }
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] button {
        background-color: #2b303b;
        color: white;
        border: 1px solid #4a4e59;
    }
    [data-testid="stSidebar"] button:hover {
        border-color: #00ace6;
        color: #00ace6;
    }
    h1, h2, h3 { color: #1a1c24; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1c24;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONE GRAFICA VISUALIZER ---
def plot_shim_bending(k_factor, stack, d_clamp, d_piston, geo_data):
    if not stack: return None
    
    max_od = max([float(x['od']) for x in stack])
    speeds = [0.5, 2.0, 6.0] # Velocità di test
    colors = ['#27ae60', '#f39c12', '#c0392b'] 
    
    # Simulazione rapida per ottenere i lift
    df_sim = SuspensionPhysics.simulate_damping_curve(k_factor, geo_data)
    
    fig, ax = plt.subplots(figsize=(8, 3.5))
    
    r_clamp = d_clamp / 2.0
    r_piston = d_piston / 2.0
    r_port = geo_data['r_port']
    
    # Disegno Meccanica
    ax.plot([0, r_piston], [0, 0], color='#2c3e50', linewidth=3, label='Pistone') 
    ax.fill_between([0, r_clamp], [0, 0], [0.5, 0.5], color='#34495e', label='Clamp')
    ax.axvline(x=r_port, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.text(r_port, -0.4, 'Port', ha='center', fontsize=8, color='gray')

    # Disegno Curve Lamelle
    for i, v_target in enumerate(speeds):
        row = df_sim.iloc[(df_sim['Velocità (m/s)'] - v_target).abs().argsort()[:1]]
        y_max = row['Lift (mm)'].values[0]
        radii, deflections = SuspensionPhysics.get_shim_profile(k_factor, d_clamp, max_od, y_max)
        
        ax.plot(radii, deflections, color=colors[i], linewidth=2, label=f'{v_target} m/s')
        ax.fill_between(radii, deflections, 0, color=colors[i], alpha=0.1)

    ax.set_title("Visualizzazione Flessione Reale", fontsize=10, fontweight='bold', color='#333')
    ax.set_ylim(-0.5, 2.5)
    ax.set_xlim(0, r_piston + 1)
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, linestyle=':', alpha=0.5)
    return fig

# --- 2. LOGIN SYSTEM ---
PASSWORD_SEGRETA = "sospensioni2025" 

if "autenticato" not in st.session_state: st.session_state["autenticato"] = False

if not st.session_state["autenticato"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div style='background-color: #f0f2f6; padding: 40px; border-radius: 12px; border: 1px solid #ccc; text-align: center;'>
            <h2 style='color:#333'>🔒 Accesso SuspensionLab</h2>
        </div><br>""", unsafe_allow_html=True)
        input_pass = st.text_input("Password", type="password")
        if st.button("ENTRA", type="primary"):
            if input_pass == PASSWORD_SEGRETA:
                st.session_state["autenticato"] = True
                st.rerun()
            else: st.error("Password Errata.")
    st.stop() 

# --- 3. BARRA LATERALE ---
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    st.markdown("---")
    
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except:
        lista_piloti = []

    pilota_sel = st.selectbox("👤 PILOTA", ["Seleziona..."] + lista_piloti)
    
    mezzo_sel = None
    id_pilota_corrente = None
    
    if pilota_sel != "Seleziona..." and lista_piloti:
        try:
            id_pilota_corrente = pilota_sel.split("(")[-1].replace(")", "")
            lista_mezzi = SuspensionDB.get_mezzi_by_pilota(id_pilota_corrente)
            mezzo_sel = st.selectbox("🏍️ MEZZO", ["Nuovo Mezzo..."] + lista_mezzi)
        except: st.error("Errore ID")

    st.markdown("---")
    st.subheader("➕ Gestione")

    with st.expander("📝 Nuovo Pilota"):
        with st.form("form_new_pilota"):
            n_nome = st.text_input("Nome")
            n_peso = st.number_input("Peso", 40, 150, 75)
            n_liv = st.selectbox("Livello", ["Amatore", "Agonista", "Pro"])
            
            if st.form_submit_button("Salva"):
                if n_nome:
                    SuspensionDB.add_pilota(n_nome, n_peso, n_liv, "", "")
                    st.success("Fatto!")
                    time.sleep(1)
                    st.rerun()

    if id_pilota_corrente:
        with st.expander("🏍️ Nuovo Mezzo"):
            with st.form("form_new_mezzo"):
                st.write(f"Per: **{pilota_sel.split('(')[0]}**")
                m_tipo = st.selectbox("Tipo", ["MOTO", "MTB"])
                m_marca = st.text_input("Marca")
                m_mod = st.text_input("Modello")
                m_anno = st.number_input("Anno", 2000, 2030, 2024)
                
                if st.form_submit_button("Salva"):
                    if m_mod:
                        SuspensionDB.add_mezzo(id_pilota_corrente, m_tipo, m_marca, m_mod, m_anno, "", "")
                        st.success("Fatto!")
                        time.sleep(1)
                        st.rerun()

# --- 4. AREA DI LAVORO ---
if mezzo_sel and mezzo_sel != "Nuovo Mezzo...":
    nome_mezzo = mezzo_sel.split("(")[0]
    tipo_mezzo = "MOTO" if "MOTO" in mezzo_sel else "MTB"
    badge_bg = "#1a1c24" 
    
    st.markdown(f"""
    ## 🛠️ {nome_mezzo}
    <span style='background-color:{badge_bg}; padding:6px 12px; border-radius:6px; color:white; font-weight:bold; font-size:0.9em; letter-spacing: 1px;'>{tipo_mezzo}</span>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    tab_setup, tab_sim, tab_diario, tab_history = st.tabs(["🔧 SETUP", "🧪 SIMULATORE", "📝 DIARIO", "🗃️ STORICO"])

    # --- TAB 1: SETUP ---
    with tab_setup:
        colA, colB = st.columns(2)
        with colA:
            st.info("**Hardware**")
            d_clamp = st.number_input("Clamp Ø (mm)", 8.0, 24.0, 12.0)
            d_pist = st.number_input("Pistone Ø (mm)", value=50.0)
        with colB:
            st.success("**Elastico & Click**")
            if "MOTO" in mezzo_sel:
                st.number_input("Molla (N/mm)", value=4.6, step=0.1)
                st.slider("Compressione", 0, 25, 12)
                st.slider("Ritorno", 0, 25, 12)
            else:
                st.number_input("Aria (PSI)", value=85)

    # --- TAB 2: SIMULATORE ---
    with tab_sim:
        st.subheader("Analisi Idraulica")
        col_geo, col_stack, col_res = st.columns([1, 1.2, 2])
        
        with col_geo:
            st.markdown("##### 1. Valvola")
            sim_d_piston = st.number_input("Ø Pistone", value=50.0, key="sdp")
            sim_r_port = st.number_input("r.port", value=12.0, help="Raggio passaggi")
            sim_w_port = st.number_input("w.port", value=8.0, help="Larghezza")
            sim_n_ports = st.number_input("N° Port", value=4)
            
            geo_data = {"d_piston": sim_d_piston, "d_rod": 16.0, "r_port": sim_r_port, "w_port": sim_w_port, "n_ports": sim_n_ports}

        with col_stack:
            st.markdown("##### 2. Stack")
            sim_d_clamp = st.number_input("Ø Clamp", value=12.0, key="sdc")
            if "sim_stack" not in st.session_state: st.session_state["sim_stack"] = []
            
            c_q, c_d, c_t = st.columns([0.8, 1, 1])
            qty = c_q.number_input("Qt", 1, 10, 1)
            od = c_d.number_input("Ø", 6.0, 44.0, 30.0)
            th = c_t.selectbox("Th", [0.10, 0.15, 0.20, 0.25, 0.30])
            
            if st.button("⬇️ Add"):
                st.session_state["sim_stack"].append({"qty": qty, "od": od, "th": th})
            
            if st.session_state["sim_stack"]:
                st.dataframe(pd.DataFrame(st.session_state["sim_stack"]), hide_index=True)
                if st.button("🗑️ Reset"):
                    st.session_state["sim_stack"] = []
                    st.rerun()

        with col_res:
            st.markdown("##### 3. Risultati")
            if st.button("🔥 CALCOLA", type="primary", use_container_width=True):
                if st.session_state["sim_stack"]:
                    k_factor = SuspensionPhysics.calculate_stiffness_factor(st.session_state["sim_stack"], sim_d_clamp, sim_d_piston)
                    df_res = SuspensionPhysics.simulate_damping_curve(k_factor, geo_data)
                    
                    st.metric("Rigidezza (K)", f"{k_factor:.1f}")
                    
                    t1, t2 = st.tabs(["Flessione", "Curva"])
                    with t1:
                        fig = plot_shim_bending(k_factor, st.session_state["sim_stack"], sim_d_clamp, sim_d_piston, geo_data)
                        st.pyplot(fig)
                    with t2:
                        st.line_chart(df_res.set_index("Velocità (m/s)")["Forza (N)"])

    # --- TAB 3: DIARIO ---
    with tab_diario:
        st.subheader("Report Sessione")
        with st.form("form_sessione"):
            c1, c2 = st.columns(2)
            f_pista = c1.text_input("📍 Luogo")
            f_cond = c2.selectbox("🌤️ Condizione", ["Secco", "Fango", "Sabbia", "Sassi"])
            f_feed = st.text_area("💬 Feedback")
            f_rating = st.slider("⭐ Voto", 1, 5, 3)
            
            dt_snap = {"stack": st.session_state.get("sim_stack", []), "geo": geo_data if 'geo_data' in locals() else {}}
            
            if st.form_submit_button("💾 SALVA", type="primary"):
                if f_pista:
                    id_cl = mezzo_sel.split("(")[-1].replace(")", "")
                    SuspensionDB.save_session(id_cl, f_pista, f_cond, f_feed, f_rating, dt_snap)
                    st.success("Salvato!")
                    time.sleep(1)
                    st.rerun()

    # --- TAB 4: STORICO ---
    with tab_history:
        st.subheader("Storico Sessioni")
        id_cl = mezzo_sel.split("(")[-1].replace(")", "")
        df_st = SuspensionDB.get_history_by_mezzo(id_cl)
        
        if df_st.empty: st.info("Nessuna sessione.")
        else:
            for _, row in df_st.iterrows():
                with st.expander(f"📅 {row['data']} - {row['pista_luogo']} (Voto: {row['rating']})"):
                    st.write(f"_{row['feedback_text']}_")
                    try:
                        st.json(json.loads(row['dati_tecnici_json']))
                    except: pass

else:
    st.title("🛠️ SuspensionLab")
    st.info("👈 Seleziona un Pilota dal menu.")
