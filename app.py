import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import time

# --- IMPORT MODULI ---
# Ora che il server va, carichiamo i moduli completi
try:
    from db_manager import SuspensionDB
    from physics import SuspensionPhysics
except ImportError:
    st.error("⚠️ ERRORE: Assicurati che db_manager.py e physics.py siano presenti.")
    st.stop()

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="SuspensionLab",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS ORIGINALE (Dark Sidebar & Pulsanti) ---
st.markdown("""
<style>
    /* Sidebar Scura */
    [data-testid="stSidebar"] {
        background-color: #1a1c24;
        border-right: 1px solid #333;
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    /* Input e Selectbox nella Sidebar */
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] input {
        background-color: #2b303b !important;
        color: white !important;
        border: 1px solid #4a4e59 !important;
    }
    /* Bottoni */
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
    }
    /* Metriche */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONE GRAFICA VISUALIZER (Quella bella) ---
def plot_shim_bending(k_factor, stack, d_clamp, d_piston, geo_data):
    if not stack: return None
    
    # Parametri grafici
    max_od = max([float(x['od']) for x in stack])
    speeds = [0.5, 2.0, 6.0] # Velocità simulate
    colors = ['#2ecc71', '#f1c40f', '#e74c3c'] # Verde, Giallo, Rosso
    
    # Simulazione per ottenere i lift
    df_sim = SuspensionPhysics.simulate_damping_curve(k_factor, geo_data)
    
    fig, ax = plt.subplots(figsize=(8, 3.5))
    # Colore di sfondo scuro per contrasto professionale
    fig.patch.set_facecolor('#ffffff') 
    
    r_clamp = d_clamp / 2.0
    r_piston = d_piston / 2.0
    r_port = geo_data['r_port']
    
    # Disegno Componenti Fissi (Pistone e Clamp)
    ax.plot([0, r_piston], [0, 0], color='#2c3e50', linewidth=4, label='Pistone') 
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

    ax.set_title("Visualizzazione Flessione Reale (Scala 1:1)", fontsize=10, fontweight='bold', color='#333')
    ax.set_ylim(-0.5, 3.0)
    ax.set_xlim(0, r_piston + 2)
    ax.legend(loc='upper left', fontsize=8, frameon=True)
    ax.grid(True, linestyle=':', alpha=0.3)
    plt.tight_layout()
    return fig

# --- SISTEMA LOGIN ---
if "autenticato" not in st.session_state: st.session_state["autenticato"] = False

if not st.session_state["autenticato"]:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("🔒 Accesso Riservato SuspensionLab")
        input_pass = st.text_input("Inserisci Password", type="password")
        if st.button("ENTRA", type="primary", use_container_width=True):
            if input_pass == "sospensioni2025":
                st.session_state["autenticato"] = True
                st.rerun()
            else:
                st.error("Password Errata.")
    st.stop() 

# --- SIDEBAR & GESTIONE DATI COMPLETA ---
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    st.markdown("---")
    
    # 1. SELEZIONE PILOTA
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except Exception as e:
        st.error(f"Err DB: {e}")
        lista_piloti = []

    pilota_sel = st.selectbox("👤 PILOTA", ["Seleziona..."] + lista_piloti)
    
    # 2. SELEZIONE MEZZO
    mezzo_sel = None
    id_pilota_corrente = None
    
    if pilota_sel != "Seleziona..." and lista_piloti:
        id_pilota_corrente = pilota_sel.split("(")[-1].replace(")", "")
        lista_mezzi = SuspensionDB.get_mezzi_by_pilota(id_pilota_corrente)
        
        if lista_mezzi:
            mezzo_sel = st.selectbox("🏍️ MEZZO", ["Nuovo Mezzo..."] + lista_mezzi)
        else:
            mezzo_sel = "Nuovo Mezzo..."
            st.info("Nessuna moto. Aggiungine una sotto.")

    st.markdown("---")
    st.subheader("➕ Gestione Rapida")

    # 3. FORM NUOVO PILOTA (Come richiesto)
    with st.expander("📝 Nuovo Pilota"):
        with st.form("new_p", clear_on_submit=True):
            n_nome = st.text_input("Nome Cognome")
            n_tel = st.text_input("Telefono")
            n_peso = st.number_input("Peso (kg)", 40, 150, 75)
            n_liv = st.selectbox("Livello", ["Amatore", "Agonista", "Pro"])
            n_note = st.text_area("Note")
            if st.form_submit_button("Salva Pilota"):
                if n_nome:
                    SuspensionDB.add_pilota(n_nome, n_peso, n_liv, n_tel, n_note)
                    st.success("Salvato!")
                    time.sleep(1)
                    st.rerun()

    # 4. FORM NUOVO MEZZO (Come richiesto)
    if id_pilota_corrente:
        with st.expander("🏍️ Aggiungi Moto"):
            with st.form("new_m", clear_on_submit=True):
                st.write(f"Per: **{pilota_sel.split('(')[0]}**")
                m_tipo = st.selectbox("Tipo", ["MOTO", "MTB"])
                m_marca = st.text_input("Marca")
                m_mod = st.text_input("Modello")
                m_anno = st.number_input("Anno", 2000, 2030, 2024)
                if st.form_submit_button("Salva Moto"):
                    if m_mod:
                        SuspensionDB.add_mezzo(id_pilota_corrente, m_tipo, m_marca, m_mod, m_anno, "", "")
                        st.success("Ok!")
                        time.sleep(1)
                        st.rerun()

# --- INTERFACCIA PRINCIPALE ---
if mezzo_sel and mezzo_sel != "Nuovo Mezzo..." and mezzo_sel != "Seleziona...":
    nome_mezzo = mezzo_sel.split("(")[0]
    
    # Header Pro
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"## 🛠️ {nome_mezzo} <span style='font-size:0.5em; color:gray'>Workspace</span>", unsafe_allow_html=True)
    with col_h2:
        if st.button("Logout"):
            st.session_state["autenticato"] = False
            st.rerun()
    
    st.markdown("---")

    # LE TAB COMPLETE (Quelle che mancavano)
    tab_setup, tab_sim, tab_diario, tab_history = st.tabs(["🔧 SETUP ATTUALE", "🧪 SIMULATORE IDRAULICA", "📝 DIARIO TEST", "🗃️ STORICO"])

    # --- TAB 1: SETUP ---
    with tab_setup:
        st.subheader("Configurazione Attuale")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info("Sospensione Anteriore")
            st.number_input("Molla (N/mm o Bar)", 0.0, 200.0, 4.6, step=0.1, key="k_fork")
            st.number_input("Comp (Click)", 0, 30, 12, key="c_fork")
            st.number_input("Reb (Click)", 0, 30, 12, key="r_fork")
            st.text_input("Livello Olio / Note", "Standard")
        with c2:
            st.warning("Sospensione Posteriore")
            st.number_input("Molla (N/mm o Lbs)", 0.0, 800.0, 54.0, step=1.0, key="k_shock")
            st.number_input("Comp High (Click)", 0, 30, 10, key="ch_shock")
            st.number_input("Comp Low (Click)", 0, 30, 12, key="cl_shock")
            st.number_input("Reb (Click)", 0, 30, 12, key="r_shock")
        with c3:
            st.success("Geometria & Varie")
            st.number_input("Sag Statico (mm)", 0, 100, 35)
            st.number_input("Sag Rider (mm)", 0, 200, 105)
            st.text_input("Posizione Forcelle", "2a tacca")
            st.text_area("Note Setup", "Setting base manuale")

    # --- TAB 2: SIMULATORE (CUORE DEL SISTEMA) ---
    with tab_sim:
        st.subheader("Analisi Avanzata Stack")
        
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

        # B. INPUT STACK (Interattivo)
        with col_stack:
            st.markdown("##### 2. Stack Lamelle")
            with st.container(border=True):
                sim_d_clamp = st.number_input("Ø Clamp (mm)", value=12.0, key="dc")
                
                if "sim_stack" not in st.session_state: st.session_state["sim_stack"] = []
                
                # Input riga singola
                cc1, cc2, cc3 = st.columns([0.8, 1, 1])
                qty = cc1.number_input("Qt", 1, 10, 1)
                od = cc2.number_input("Ø Est", 6.0, 44.0, 30.0, step=1.0)
                th = cc3.selectbox("Spessore", [0.10, 0.15, 0.20, 0.25, 0.30])
                
                if st.button("⬇️ Aggiungi Lamella", use_container_width=True):
                    st.session_state["sim_stack"].append({"qty": qty, "od": od, "th": th})
                
                # Tabella Stack
                if st.session_state["sim_stack"]:
                    st.dataframe(pd.DataFrame(st.session_state["sim_stack"]), hide_index=True, use_container_width=True)
                    if st.button("🗑️ Reset Stack", use_container_width=True):
                        st.session_state["sim_stack"] = []
                        st.rerun()

        # C. OUTPUT GRAFICI
        with col_res:
            st.markdown("##### 3. Analisi")
            if st.button("🔥 CALCOLA ANALISI COMPLETA", type="primary", use_container_width=True):
                if st.session_state["sim_stack"]:
                    # Calcoli Fisici
                    k_factor = SuspensionPhysics.calculate_stiffness_factor(
                        st.session_state["sim_stack"], sim_d_clamp, sim_d_piston
                    )
                    df_res = SuspensionPhysics.simulate_damping_curve(k_factor, geo_data)
                    
                    # Metriche
                    m1, m2 = st.columns(2)
                    m1.metric("Rigidezza (K)", f"{k_factor:.1f}")
                    m2.metric("Forza Max @ 6m/s", f"{df_res['Forza (N)'].max():.0f} N")
                    
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

    # --- TAB 3: DIARIO (FEEDBACK) ---
    with tab_diario:
        st.subheader("Report Sessione")
        with st.form("diario_form"):
            c1, c2 = st.columns(2)
            f_pista = c1.text_input("📍 Pista / Luogo")
            f_cond = c2.selectbox("🌤️ Condizione", ["Secco", "Fango", "Sabbia", "Sassi", "Misto", "Bagnato"])
            f_feed = st.text_area("💬 Feedback Pilota (Sensazioni, problemi, modifiche richieste)")
            f_rating = st.slider("⭐ Voto Generale Sessione", 1, 5, 3)
            
            # Snapshot dati tecnici attuali (per salvarli nello storico)
            snapshot = {
                "stack": st.session_state.get("sim_stack", []),
                "geo": geo_data if 'geo_data' in locals() else {}
            }
            
            if st.form_submit_button("💾 ARCHIVIA SESSIONE", type="primary"):
                if f_pista:
                    id_m = mezzo_sel.split("(")[-1].replace(")", "")
                    SuspensionDB.save_session(id_m, f_pista, f_cond, f_feed, f_rating, snapshot)
                    st.success("Sessione Salvata nel Database!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Inserisci almeno il nome della pista.")

    # --- TAB 4: STORICO ---
    with tab_history:
        st.subheader("Storico Sessioni")
        id_m = mezzo_sel.split("(")[-1].replace(")", "")
        df_hist = SuspensionDB.get_history_by_mezzo(id_m)
        
        if df_hist.empty:
            st.info("Nessuna sessione trovata per questo mezzo.")
        else:
            for _, row in df_hist.iterrows():
                with st.expander(f"📅 {row['data']} - {row['pista_luogo']} (Voto: {row['rating']})"):
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        st.markdown(f"**Condizione:** {row['condizione']}")
                        st.markdown(f"**Feedback:**\n{row['feedback_text']}")
                    with col_b:
                        try:
                            dati = json.loads(row['dati_tecnici_json'])
                            if dati.get('stack'):
                                st.caption("🔧 Stack usato:")
                                st.dataframe(pd.DataFrame(dati['stack']), hide_index=True)
                        except:
                            st.caption("Nessun dato tecnico salvato.")

else:
    # Pagina di benvenuto vuota
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("👈 Per iniziare, seleziona un Pilota dal menu laterale.")
        st.markdown("Se è un nuovo cliente, usa **'Nuovo Pilota'** nella barra laterale.")
