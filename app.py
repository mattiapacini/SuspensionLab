import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time

# --- IMPORT MODULI ---
try:
    from db_manager import SuspensionDB
    from physics import SuspensionPhysics
except ImportError:
    st.error("⚠️ ERRORE: Mancano i file db_manager.py o physics.py")
    st.stop()

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="SuspensionLab", page_icon="🔧", layout="wide")

# --- CSS DARK MODE & UI FIX ---
st.markdown("""
<style>
    /* 1. SIDEBAR SCURA TOTALE */
    [data-testid="stSidebar"] {
        background-color: #1a1c24;
        border-right: 1px solid #333;
    }
    
    /* 2. TESTI SIDEBAR BIANCHI */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p {
        color: #e0e0e0 !important;
    }

    /* 3. MENU A TENDINA E INPUT (FIX BIANCO) */
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="input"] > div {
        background-color: #2b303b !important;
        color: white !important;
        border-color: #4a4e59 !important;
    }
    [data-testid="stSidebar"] input {
        color: white !important;
    }
    /* Colore opzioni menu a tendina */
    div[role="listbox"] ul {
        background-color: #2b303b !important;
    }
    
    /* 4. BOTTONI SIDEBAR */
    [data-testid="stSidebar"] button {
        background-color: #00ace6;
        color: white;
        border: none;
        font-weight: bold;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #0086b3;
    }

    /* 5. STILE TAB */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
        font-weight: 600;
    }
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
    
    ax.plot([0, r_piston], [0, 0], color='#2c3e50', linewidth=3)
    ax.fill_between([0, r_clamp], [0, 0], [0.5, 0.5], color='#34495e')
    ax.axvline(x=r_port, color='gray', linestyle='--', alpha=0.5)

    for i, v in enumerate(speeds):
        row = df_sim.iloc[(df_sim['Velocità (m/s)'] - v).abs().argsort()[:1]]
        y_max = row['Lift (mm)'].values[0]
        radii, deflections = SuspensionPhysics.get_shim_profile(k_factor, d_clamp, max_od, y_max)
        ax.plot(radii, deflections, color=colors[i], label=f'{v} m/s')
        ax.fill_between(radii, deflections, 0, color=colors[i], alpha=0.1)

    ax.set_ylim(-0.5, 2.5)
    ax.legend(fontsize=8)
    ax.grid(True, linestyle=':', alpha=0.5)
    return fig

# --- INIZIO LOGICA APP ---

# 1. LOGIN
if "autenticato" not in st.session_state: st.session_state["autenticato"] = False
if not st.session_state["autenticato"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.container(border=True):
            st.subheader("🔒 Accesso Lab")
            pwd = st.text_input("Password", type="password")
            if st.button("ENTRA", type="primary", use_container_width=True):
                if pwd == "sospensioni2025":
                    st.session_state["autenticato"] = True
                    st.rerun()
    st.stop()

# 2. SIDEBAR (NAVIGATORE)
with st.sidebar:
    st.title("🗂️ NAVIGATORE")
    st.markdown("---")
    
    # Caricamento Piloti
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except:
        st.error("Errore DB")
        lista_piloti = []

    # Dropdown Pilota (Ora Dark Mode)
    pilota_sel = st.selectbox("👤 SELEZIONA PILOTA", ["..."] + lista_piloti)
    
    # Gestione Selezione
    id_pilota_corrente = None
    mezzo_sel = None
    
    if pilota_sel != "..." and lista_piloti:
        id_pilota_corrente = pilota_sel.split("(")[-1].replace(")", "")
        try:
            lista_mezzi = SuspensionDB.get_mezzi_by_pilota(id_pilota_corrente)
            mezzo_sel = st.selectbox("🏍️ SELEZIONA MEZZO", ["Nuovo Mezzo..."] + lista_mezzi)
        except:
            pass
            
    st.markdown("---")
    if st.button("Esci"):
        st.session_state["autenticato"] = False
        st.rerun()

# 3. INTERFACCIA PRINCIPALE
st.title("SuspensionLab Manager")

# Tabs principali riorganizzate
tab_gestione, tab_sim, tab_diario = st.tabs(["👥 GESTIONE & GARAGE", "🧪 SIMULATORE PRO", "📝 DIARIO TEST"])

# --- TAB 1: GESTIONE (ORDINATA) ---
with tab_gestione:
    # Due colonne o sotto-tab per separare "Nuovo" da "Esistente"
    sub_t1, sub_t2 = st.tabs(["➕ REGISTRA NUOVO", "📂 FASCICOLO PILOTA"])
    
    # A. NUOVO INSERIMENTO
    with sub_t1:
        st.subheader("Inserimento Nuovo Cliente")
        with st.container(border=True):
            with st.form("new_user_form", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                n_nome = col_a.text_input("Nome e Cognome*")
                n_tel = col_b.text_input("Telefono")
                
                col_c, col_d = st.columns(2)
                n_peso = col_c.number_input("Peso (kg)", 40, 150, 75)
                n_liv = col_d.selectbox("Livello", ["Amatore", "Agonista", "Pro"])
                
                n_note = st.text_area("Note Fisiche / Generali")
                
                if st.form_submit_button("💾 SALVA CLIENTE NEL DB", type="primary"):
                    if n_nome:
                        SuspensionDB.add_pilota(n_nome, n_peso, n_liv, n_tel, n_note)
                        st.toast("✅ Cliente Salvato!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Inserisci il nome.")

    # B. DATI ESISTENTI
    with sub_t2:
        if id_pilota_corrente:
            col_info, col_garage = st.columns([1, 2])
            
            with col_info:
                st.info(f"**Pilota:** {pilota_sel.split('(')[0]}")
                # Qui potresti chiamare una funzione per i dettagli, per ora statico
                st.write(f"ID: `{id_pilota_corrente}`")
            
            with col_garage:
                st.subheader("Garage Moto")
                # Form per aggiungere moto a QUESTO pilota
                with st.expander("🏍️ Aggiungi Moto a questo pilota"):
                    with st.form("add_bike"):
                        m_tipo = st.selectbox("Tipo", ["MOTO", "MTB"])
                        c1, c2, c3 = st.columns(3)
                        m_marca = c1.text_input("Marca")
                        m_mod = c2.text_input("Modello")
                        m_anno = c3.number_input("Anno", 2000, 2030, 2024)
                        
                        if st.form_submit_button("Aggiungi Mezzo"):
                            if m_mod:
                                SuspensionDB.add_mezzo(id_pilota_corrente, m_tipo, m_marca, m_mod, m_anno, "", "")
                                st.success("Mezzo aggiunto!")
                                time.sleep(1)
                                st.rerun()
                
                # Lista mezzi esistenti
                if mezzo_sel and mezzo_sel != "Nuovo Mezzo...":
                    st.success(f"Mezzo Attivo: **{mezzo_sel}**")
                else:
                    st.warning("Nessun mezzo selezionato o garage vuoto.")

        else:
            st.info("👈 Seleziona un Pilota dal menu laterale per vedere il suo fascicolo.")

# --- TAB 2: SIMULATORE ---
with tab_sim:
    if not mezzo_sel or mezzo_sel == "Nuovo Mezzo...":
        st.warning("Seleziona una moto dal menu laterale per iniziare a lavorare.")
    else:
        st.subheader(f"Analisi Idraulica: {mezzo_sel.split('(')[0]}")
        
        c_input, c_out = st.columns([1, 2])
        
        with c_input:
            with st.expander("1. Geometria Valvola", expanded=True):
                geo_data = {
                    "d_piston": st.number_input("Ø Pistone", value=50.0),
                    "d_rod": 16.0,
                    "r_port": st.number_input("r.port (Leva)", value=12.0),
                    "w_port": 8.0, "n_ports": 4
                }
            
            with st.expander("2. Stack Lamelle", expanded=True):
                st.caption("Aggiungi dal basso verso l'alto")
                d_clamp = st.number_input("Ø Clamp", value=12.0)
                
                if "sim_stack" not in st.session_state: st.session_state["sim_stack"] = []
                
                cc1, cc2, cc3 = st.columns([0.7, 1, 1])
                qty = cc1.number_input("Qt", 1, 10, 1)
                od = cc2.number_input("Ø", 6.0, 44.0, 30.0)
                th = cc3.selectbox("Th", [0.10, 0.15, 0.20, 0.25, 0.30])
                
                if st.button("⬇️ Aggiungi", use_container_width=True):
                    st.session_state["sim_stack"].append({"qty": qty, "od": od, "th": th})
                
                if st.session_state["sim_stack"]:
                    st.dataframe(pd.DataFrame(st.session_state["sim_stack"]), hide_index=True)
                    if st.button("🗑️ Reset Stack"):
                        st.session_state["sim_stack"] = []
                        st.rerun()

        with c_out:
            if st.button("🔥 CALCOLA RISPOSTA", type="primary", use_container_width=True):
                if st.session_state["sim_stack"]:
                    k = SuspensionPhysics.calculate_stiffness_factor(st.session_state["sim_stack"], d_clamp, geo_data["d_piston"])
                    df_res = SuspensionPhysics.simulate_damping_curve(k, geo_data)
                    
                    m1, m2 = st.columns(2)
                    m1.metric("K Rigidezza", f"{k:.1f}")
                    m2.metric("Forza Max", f"{df_res['Forza (N)'].max():.0f} N")
                    
                    t_g1, t_g2 = st.tabs(["Flessione Reale", "Grafico Forza"])
                    with t_g1:
                        st.pyplot(plot_shim_bending(k, st.session_state["sim_stack"], d_clamp, geo_data["d_piston"], geo_data))
                    with t_g2:
                        st.line_chart(df_res.set_index("Velocità (m/s)")["Forza (N)"])

# --- TAB 3: DIARIO ---
with tab_diario:
    if not mezzo_sel or mezzo_sel == "Nuovo Mezzo...":
        st.warning("Seleziona una moto per visualizzare o scrivere il diario.")
    else:
        id_m = mezzo_sel.split("(")[-1].replace(")", "")
        
        st.subheader("Nuovo Report")
        with st.form("diario"):
            row1 = st.columns(2)
            pista = row1[0].text_input("📍 Pista")
            cond = row1[1].selectbox("🌤️ Condizione", ["Secco", "Fango", "Sabbia", "Misto"])
            feed = st.text_area("💬 Feedback")
            voto = st.slider("Voto", 1, 5, 3)
            
            if st.form_submit_button("Salva Report"):
                SuspensionDB.save_session(id_m, pista, cond, feed, voto, {})
                st.success("Salvato!")
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        st.subheader("Storico")
        df_hist = SuspensionDB.get_history_by_mezzo(id_m)
        if not df_hist.empty:
            st.dataframe(df_hist[['data', 'pista_luogo', 'rating', 'feedback_text']], use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna sessione precedente.")
