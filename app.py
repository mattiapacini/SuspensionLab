import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from physics import SuspensionPhysics
from db_manager import SuspensionDB

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(layout="wide", page_title="SuspensionLab PRO", page_icon="⚙️")
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #1E1E1E; border-radius: 5px; color: white; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #E67E22; color: white; }
    div[data-testid="stToast"] { background-color: #2ecc71; color: white; }
    .block-container { padding-top: 1rem; }
    hr { margin: 10px 0; border-color: #444; }
</style>
""", unsafe_allow_html=True)

# --- INIT STATE ---
def init_state():
    defaults = {
        "fork_bv_df": pd.DataFrame([{"qty": 1, "od": 20.0, "th": 0.15}, {"qty": 1, "od": 18.0, "th": 0.15}]),
        "fork_mv_df": pd.DataFrame([{"qty": 1, "od": 20.0, "th": 0.10}]),
        "shock_comp_df": pd.DataFrame([{"qty": 1, "od": 40.0, "th": 0.20}, {"qty": 1, "od": 30.0, "th": 0.15}]),
        "shock_reb_df": pd.DataFrame([{"qty": 1, "od": 36.0, "th": 0.15}]),
        "current_pilot_id": None,
        "current_bike_id": None,
        "rider_weight": 80
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

# --- HELPER FUNCS ---
def render_stack(key):
    return st.data_editor(
        st.session_state[f"{key}_df"],
        num_rows="dynamic",
        column_config={
            "qty": st.column_config.NumberColumn("Q", min_value=1, max_value=20, step=1, format="%d"),
            "od": st.column_config.NumberColumn("Ø", min_value=6.0, max_value=60.0, step=0.5, format="%.1f"),
            "th": st.column_config.NumberColumn("Th", min_value=0.05, max_value=1.0, step=0.01, format="%.2f")
        },
        use_container_width=True,
        key=f"ed_{key}"
    )

def calc_k(df):
    k = 0.0
    try:
        for _, r in df.iterrows(): k += (r['th']**3) * r['qty'] * 1000
    except: pass
    return max(k, 0.1)

# ==============================================================================
# SIDEBAR: GESTIONE SCUDERIA (Pilota -> Moto -> Sessione)
# ==============================================================================
with st.sidebar:
    st.title("🏎️ Scuderia")
    
    # 1. SELEZIONE PILOTA
    st.markdown("### 👤 Pilota")
    df_piloti = SuspensionDB.get_piloti()
    
    opts_piloti = ["➕ NUOVO PILOTA"] + df_piloti.apply(lambda x: f"{x['Nome']} (ID:{x['ID']})", axis=1).tolist() if not df_piloti.empty else ["➕ NUOVO PILOTA"]
    sel_pilota = st.selectbox("Seleziona:", opts_piloti, label_visibility="collapsed")
    
    if sel_pilota == "➕ NUOVO PILOTA":
        with st.form("new_pilot"):
            n_nome = st.text_input("Nome")
            n_peso = st.number_input("Peso (kg)", 40, 120, 80)
            n_liv = st.selectbox("Livello", ["Amatore", "Pro", "Expert"])
            n_tel = st.text_input("Telefono")
            n_note = st.text_area("Note")
            if st.form_submit_button("Crea Pilota"):
                SuspensionDB.add_pilota(n_nome, n_peso, n_liv, n_tel, n_note)
                st.rerun()
        st.stop()
    else:
        # Recupera dati Pilota
        pid_idx = opts_piloti.index(sel_pilota) - 1
        curr_pilot = df_piloti.iloc[pid_idx]
        st.session_state["current_pilot_id"] = curr_pilot["ID"]
        st.session_state["rider_weight"] = float(curr_pilot["Peso"]) if pd.notna(curr_pilot["Peso"]) else 80.0
        st.caption(f"Peso: {st.session_state['rider_weight']}kg | Liv: {curr_pilot['Livello']}")

    st.markdown("---")

    # 2. SELEZIONE MOTO (GARAGE)
    if st.session_state["current_pilot_id"]:
        st.markdown("### 🏍️ Garage")
        df_garage = SuspensionDB.get_garage(st.session_state["current_pilot_id"])
        
        opts_moto = ["➕ AGGIUNGI MOTO"] 
        if not df_garage.empty:
            opts_moto += df_garage.apply(lambda x: f"{x['marca']} {x['modello']} ({x['anno']})", axis=1).tolist()
            
        sel_moto = st.selectbox("Seleziona Moto:", opts_moto, label_visibility="collapsed")
        
        if sel_moto == "➕ AGGIUNGI MOTO":
            with st.form("new_moto"):
                m_tipo = st.selectbox("Tipo", ["Cross", "Enduro", "Motard", "Stradale"])
                c1, c2, c3 = st.columns(3)
                m_marca = c1.text_input("Marca", "KTM")
                m_mod = c2.text_input("Modello", "SX-F 450")
                m_anno = c3.number_input("Anno", 2000, 2025, 2024)
                m_forc = st.text_input("Forcella (Es. WP 48)", "WP XACT 48")
                m_mono = st.text_input("Mono (Es. Showa)", "WP XACT")
                if st.form_submit_button("Salva Moto"):
                    SuspensionDB.add_mezzo(st.session_state["current_pilot_id"], m_tipo, m_marca, m_mod, m_anno, m_forc, m_mono)
                    st.rerun()
            st.stop()
        else:
            mid_idx = opts_moto.index(sel_moto) - 1
            curr_moto = df_garage.iloc[mid_idx]
            st.session_state["current_bike_id"] = curr_moto["id_mezzo"]
            
            # 3. GESTIONE SESSIONI
            st.markdown("---")
            st.markdown("### 📋 Sessioni / Setup")
            
            # Carica Setup
            df_sess = SuspensionDB.get_sessioni(st.session_state["current_bike_id"])
            if not df_sess.empty:
                opts_sess = df_sess.apply(lambda x: f"{x['data']} | {x['pista_luogo']}", axis=1).tolist()
                sel_sess = st.selectbox("Storico:", opts_sess)
                
                if st.button("📂 CARICA SETUP", type="secondary", use_container_width=True):
                    idx_s = opts_sess.index(sel_sess)
                    row_s = df_sess.iloc[idx_s]
                    
                    # Parsing JSON tecnico
                    tech = SuspensionDB.parse_json(row_s['dati_tecnici_json'])
                    if 'f_bv' in tech: st.session_state["fork_bv_df"] = pd.DataFrame(tech['f_bv'])
                    if 'f_mv' in tech: st.session_state["fork_mv_df"] = pd.DataFrame(tech['f_mv'])
                    if 's_comp' in tech: st.session_state["shock_comp_df"] = pd.DataFrame(tech['s_comp'])
                    if 's_reb' in tech: st.session_state["shock_reb_df"] = pd.DataFrame(tech['s_reb'])
                    st.toast(f"Caricato: {row_s['pista_luogo']}")
                    st.rerun()
            else:
                st.info("Nessuna sessione per questa moto.")
            
            st.markdown("#### 💾 Salva Lavoro Corrente")
            with st.form("save_sess"):
                s_pista = st.text_input("Pista / Luogo")
                s_cond = st.selectbox("Condizione", ["Secco", "Fango", "Sabbia", "Duro", "Misto"])
                s_feed = st.text_area("Feedback Pilota", height=80)
                s_rat = st.slider("Rating", 1, 5, 3)
                
                if st.form_submit_button("SALVA SESSIONE"):
                    # Prepara il pacchetto tecnico JSON
                    tech_pack = {
                        "f_bv": st.session_state["fork_bv_df"].to_dict('records'),
                        "f_mv": st.session_state["fork_mv_df"].to_dict('records'),
                        "s_comp": st.session_state["shock_comp_df"].to_dict('records'),
                        "s_reb": st.session_state["shock_reb_df"].to_dict('records')
                    }
                    SuspensionDB.save_session(
                        st.session_state["current_bike_id"],
                        s_pista, s_cond, s_feed, s_rat, tech_pack
                    )
                    st.rerun()

# ==============================================================================
# MAIN: SIMULATORE
# ==============================================================================

if not st.session_state.get("current_bike_id"):
    st.info("👈 Per iniziare: Crea o Seleziona un Pilota, poi scegli una Moto dal menu laterale.")
    st.stop()

# TABS
t_fork, t_shock, t_chassis = st.tabs(["🔹 FORCELLA", "🔸 MONO", "⚖️ TELAIO"])

# --- FORCELLA ---
with t_fork:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("Base Valve (BV)")
        st.session_state["fork_bv_df"] = render_stack("fork_bv")
        st.subheader("Mid Valve (MV)")
        st.session_state["fork_mv_df"] = render_stack("fork_mv")
        
    with c2:
        st.subheader("Simulazione Idraulica")
        v_sim = st.slider("Velocità Visualizer (m/s)", 0.0, 6.0, 2.0, key="vf")
        
        # Fisica 
        k_bv = calc_k(st.session_state["fork_bv_df"])
        geo_f = {'d_piston': 24.0, 'd_rod': 12.0, 'type': 'compression', 'n_port': 4, 'w_port': 8.0, 'h_deck': 2.0, 'd_throat': 20.0}
        
        vels = np.linspace(0.01, 6.0, 50)
        forces = []
        lifts = []
        for v in vels:
             f, l = SuspensionPhysics.solve_damping(v, k_bv, geo_f, 1.5, 0)
             forces.append(f)
             lifts.append(l)
        
        # Plot Curve
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=vels, y=forces, mode='lines', line=dict(color='#3498db', width=3)))
        fig.update_layout(height=250, margin=dict(l=20,r=20,t=20,b=20), template="plotly_dark", title="Forza (N) vs Velocità (m/s)")
        st.plotly_chart(fig, use_container_width=True)
        
        # Visualizer
        idx = (np.abs(vels - v_sim)).argmin()
        lift = lifts[idx]
        fig_vis = go.Figure()
        x_s = np.linspace(6, 12, 20) 
        y_s = lift * ((x_s-6)/(12-6))**2
        fig_vis.add_trace(go.Scatter(x=x_s, y=y_s, line=dict(color='#3498db', width=4), name="Lamella"))
        fig_vis.add_trace(go.Scatter(x=[6, 12], y=[0,0], line=dict(color='gray', dash='dot'), name="Battuta"))
        fig_vis.update_layout(height=200, margin=dict(l=20,r=20,t=20,b=20), template="plotly_dark", yaxis_range=[-0.2, 2.0], title=f"Apertura Lamella: {lift:.2f}mm")
        st.plotly_chart(fig_vis, use_container_width=True)

# --- MONO ---
with t_shock:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("Stack Compressione")
        st.session_state["shock_comp_df"] = render_stack("shock_comp")
        st.subheader("Stack Ritorno")
        st.session_state["shock_reb_df"] = render_stack("shock_reb")
    
    with c2:
        st.subheader("Simulazione & Cavitazione")
        v_sim_s = st.slider("Velocità Visualizer (m/s)", 0.0, 6.0, 2.0, key="vs")
        
        k_sc = calc_k(st.session_state["shock_comp_df"])
        geo_s = {'d_piston': 50.0, 'd_rod': 16.0, 'type': 'compression', 'n_port': 4, 'w_port': 12.0, 'h_deck': 3.0, 'd_throat': 100}
        
        forces_s = []
        lifts_s = []
        for v in vels:
            f, l = SuspensionPhysics.solve_damping(v, k_sc, geo_s, 1.0, 0)
            forces_s.append(f)
            lifts_s.append(l)
        
        fig_s = go.Figure()
        fig_s.add_trace(go.Scatter(x=vels, y=forces_s, line=dict(color='#e74c3c', width=3)))
        # Cavitation dummy limit
        fig_s.add_hline(y=1800, line_dash="dash", line_color="red", annotation_text="Limite Cavitazione (Stimato)")
        fig_s.update_layout(height=250, margin=dict(l=20,r=20,t=20,b=20), template="plotly_dark", title="Curva Compressione Mono")
        st.plotly_chart(fig_s, use_container_width=True)
        
        idx_s = (np.abs(vels - v_sim_s)).argmin()
        lift_s = lifts_s[idx_s]
        fig_vis_s = go.Figure()
        x_ss = np.linspace(6, 25, 20)
        y_ss = lift_s * ((x_ss-6)/(25-6))**2
        fig_vis_s.add_trace(go.Scatter(x=x_ss, y=y_ss, line=dict(color='#e74c3c', width=4)))
        fig_vis_s.add_trace(go.Scatter(x=[6, 25], y=[0,0], line=dict(color='gray', dash='dot')))
        fig_vis_s.update_layout(height=200, margin=dict(l=20,r=20,t=20,b=20), template="plotly_dark", yaxis_range=[-0.2, 2.5], title=f"Apertura Mono: {lift_s:.2f}mm")
        st.plotly_chart(fig_vis_s, use_container_width=True)

# --- TELAIO ---
with t_chassis:
    st.subheader("⚖️ Calcolatore Bilanciamento")
    
    col_w1, col_w2 = st.columns(2)
    rider_w_actual = st.session_state.get("rider_weight", 80.0)
    
    with col_w1:
        st.metric("Peso Pilota Attuale", f"{rider_w_actual} kg")
    with col_w2:
        target_w = st.number_input("Peso Target (Standard)", 50, 120, 75)
        
    ratio = rider_w_actual / target_w
    
    st.markdown("#### Suggerimenti Setup")
    c1, c2, c3 = st.columns(3)
    
    spring_change = (ratio - 1) * 100
    hyd_change = (np.sqrt(ratio) - 1) * 100
    
    c1.info(f"Molla: **{spring_change:+.1f}%** Rigidità")
    c2.warning(f"Idraulica: **{hyd_change:+.1f}%** Frenatura")
    c3.success("Sag consigliato: **35mm** Statico / **105mm** Rider")
    
    st.caption("Nota: I calcoli si basano sulla variazione di frequenza naturale del sistema massa-molla.")
