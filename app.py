import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from physics import SuspensionPhysics
from db_manager import SuspensionDB

# --- CONFIGURAZIONE ---
st.set_page_config(layout="wide", page_title="SuspensionLab PRO", page_icon="⚙️")
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #1E1E1E; border-radius: 5px; color: white; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #E67E22; color: white; }
    .block-container { padding-top: 1rem; }
    hr { margin: 10px 0; border-color: #444; }
</style>
""", unsafe_allow_html=True)

# --- INIT STATE ---
if "init_done" not in st.session_state:
    st.session_state.update({
        "fork_bv_df": pd.DataFrame([{"qty": 1, "od": 20.0, "th": 0.15}, {"qty": 1, "od": 18.0, "th": 0.15}]),
        "fork_mv_df": pd.DataFrame([{"qty": 1, "od": 20.0, "th": 0.10}]),
        "shock_comp_df": pd.DataFrame([{"qty": 1, "od": 40.0, "th": 0.20}, {"qty": 1, "od": 30.0, "th": 0.15}]),
        "shock_reb_df": pd.DataFrame([{"qty": 1, "od": 36.0, "th": 0.15}]),
        "current_pilot_id": None,
        "current_bike_id": None,
        "rider_weight": 80.0,
        "init_done": True
    })

# --- HELPER FUNCTIONS ---
def render_stack(key):
    """Renderizza la tabella editabile per gli spessori"""
    return st.data_editor(
        st.session_state[f"{key}_df"],
        num_rows="dynamic",
        column_config={
            "qty": st.column_config.NumberColumn("Q.tà", min_value=1, max_value=20, step=1, format="%d"),
            "od": st.column_config.NumberColumn("Ø Esterno", min_value=6.0, max_value=60.0, step=0.5, format="%.1f"),
            "th": st.column_config.NumberColumn("Spessore", min_value=0.05, max_value=1.0, step=0.01, format="%.2f")
        },
        use_container_width=True,
        key=f"editor_{key}"
    )

def calc_k(df):
    """Calcola la rigidezza approssimativa dello stack"""
    k = 0.0
    try:
        for _, r in df.iterrows(): k += (r['th']**3) * r['qty'] * 1000
    except: pass
    return max(k, 0.1)

# ==============================================================================
# SIDEBAR: GESTIONE SCUDERIA
# ==============================================================================
with st.sidebar:
    st.title("🏎️ Scuderia")
    
    # 1. PILOTA
    df_piloti = SuspensionDB.get_piloti()
    # Costruiamo la lista opzioni
    opts_piloti = ["➕ NUOVO PILOTA"] 
    if not df_piloti.empty:
        opts_piloti += df_piloti.apply(lambda x: f"{x['Nome']} (ID:{x['ID']})", axis=1).tolist()
    
    sel_pilota = st.selectbox("👤 Pilota", opts_piloti)
    
    if sel_pilota == "➕ NUOVO PILOTA":
        with st.form("new_pilot"):
            st.write("**Crea Nuovo Pilota**")
            n_nome = st.text_input("Nome e Cognome")
            n_peso = st.number_input("Peso (kg)", 40, 120, 80)
            n_liv = st.selectbox("Livello", ["Amatore", "Pro", "Expert"])
            n_tel = st.text_input("Telefono")
            if st.form_submit_button("Salva Pilota"):
                SuspensionDB.add_pilota(n_nome, n_peso, n_liv, n_tel, "")
                st.rerun()
        st.stop()
    else:
        # Estrai ID dal menu
        try:
            pid_idx = opts_piloti.index(sel_pilota) - 1
            curr_pilot = df_piloti.iloc[pid_idx]
            st.session_state["current_pilot_id"] = curr_pilot["ID"]
            st.session_state["rider_weight"] = float(curr_pilot["Peso"]) if pd.notna(curr_pilot["Peso"]) else 80.0
        except: pass

    st.markdown("---")

    # 2. MOTO
    if st.session_state["current_pilot_id"]:
        df_garage = SuspensionDB.get_garage(st.session_state["current_pilot_id"])
        
        opts_moto = ["➕ AGGIUNGI MOTO"]
        if not df_garage.empty:
            opts_moto += df_garage.apply(lambda x: f"{x['marca']} {x['modello']} ({x['anno']})", axis=1).tolist()
            
        sel_moto = st.selectbox("🏍️ Garage", opts_moto)
        
        if sel_moto == "➕ AGGIUNGI MOTO":
            with st.form("new_moto"):
                st.write("**Aggiungi Moto**")
                m_marca = st.text_input("Marca", "KTM")
                m_mod = st.text_input("Modello", "SX-F 450")
                m_anno = st.number_input("Anno", 2000, 2025, 2024)
                if st.form_submit_button("Salva Moto"):
                    SuspensionDB.add_mezzo(st.session_state["current_pilot_id"], "Cross", m_marca, m_mod, m_anno, "", "")
                    st.rerun()
            st.stop()
        else:
            try:
                mid_idx = opts_moto.index(sel_moto) - 1
                curr_moto = df_garage.iloc[mid_idx]
                st.session_state["current_bike_id"] = curr_moto["id_mezzo"]
            except: pass

            # 3. SESSIONI
            st.markdown("---")
            st.markdown("### 📋 Sessioni")
            
            df_sess = SuspensionDB.get_sessioni(st.session_state["current_bike_id"])
            if not df_sess.empty:
                opts_sess = df_sess.apply(lambda x: f"{x['data']} | {x['pista_luogo']}", axis=1).tolist()
                sel_sess = st.selectbox("Storico:", opts_sess)
                
                if st.button("📂 CARICA SETUP", use_container_width=True):
                    idx_s = opts_sess.index(sel_sess)
                    row_s = df_sess.iloc[idx_s]
                    
                    tech = SuspensionDB.parse_json(row_s['dati_tecnici_json'])
                    if 'f_bv' in tech: st.session_state["fork_bv_df"] = pd.DataFrame(tech['f_bv'])
                    if 'f_mv' in tech: st.session_state["fork_mv_df"] = pd.DataFrame(tech['f_mv'])
                    if 's_comp' in tech: st.session_state["shock_comp_df"] = pd.DataFrame(tech['s_comp'])
                    if 's_reb' in tech: st.session_state["shock_reb_df"] = pd.DataFrame(tech['s_reb'])
                    st.toast(f"Setup caricato: {row_s['pista_luogo']}")
                    st.rerun()
            
            st.markdown("#### 💾 Salva Lavoro")
            with st.form("save_sess"):
                s_pista = st.text_input("Pista / Luogo")
                s_cond = st.selectbox("Condizione", ["Secco", "Fango", "Sabbia", "Duro", "Misto"])
                s_feed = st.text_area("Feedback Pilota", height=80)
                
                if st.form_submit_button("SALVA SESSIONE CORRENTE"):
                    tech_pack = {
                        "f_bv": st.session_state["fork_bv_df"].to_dict('records'),
                        "f_mv": st.session_state["fork_mv_df"].to_dict('records'),
                        "s_comp": st.session_state["shock_comp_df"].to_dict('records'),
                        "s_reb": st.session_state["shock_reb_df"].to_dict('records')
                    }
                    SuspensionDB.save_session(
                        st.session_state["current_bike_id"],
                        s_pista, s_cond, s_feed, 3, tech_pack
                    )
                    st.rerun()

# ==============================================================================
# MAIN: SIMULATORE COMPLETO
# ==============================================================================

if not st.session_state.get("current_bike_id"):
    st.info("👈 Per iniziare, seleziona un Pilota e una Moto dalla barra laterale.")
    st.stop()

# TABS
t_fork, t_shock, t_chassis = st.tabs(["🔹 FORCELLA", "🔸 MONO", "⚖️ TELAIO"])

# --- TAB 1: FORCELLA ---
with t_fork:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("Base Valve (BV)")
        st.session_state["fork_bv_df"] = render_stack("fork_bv")
        st.subheader("Mid Valve (MV)")
        st.session_state["fork_mv_df"] = render_stack("fork_mv")
        
    with c2:
        st.subheader("Simulazione Idraulica")
        v_sim = st.slider("Velocità Simulazione (m/s)", 0.0, 6.0, 2.0, key="vf")
        
        # Fisica 
        k_bv = calc_k(st.session_state["fork_bv_df"])
        geo_f = {'d_piston': 24.0, 'd_rod': 12.0, 'type': 'compression', 'n_port': 4, 'w_port': 8.0, 'h_deck': 2.0, 'd_throat': 20.0}
        
        vels = np.linspace(0.01, 6.0, 50)
        forces = []
        lifts = []
        
        # Calcolo curve
        for v in vels:
             f, l = SuspensionPhysics.solve_damping(v, k_bv, geo_f, 1.5, 0)
             forces.append(f)
             lifts.append(l)
        
        # Plot Curva Damping
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=vels, y=forces, mode='lines', line=dict(color='#3498db', width=3), name="Forza"))
        fig.update_layout(height=250, margin=dict(l=20,r=20,t=30,b=20), template="plotly_dark", title="Curva Smorzamento (Forza vs Velocità)")
        st.plotly_chart(fig, use_container_width=True)
        
        # Plot Visualizer (Lamella che si piega)
        idx = (np.abs(vels - v_sim)).argmin()
        lift = lifts[idx]
        fig_vis = go.Figure()
        x_s = np.linspace(6, 12, 20) 
        y_s = lift * ((x_s-6)/(12-6))**2
        fig_vis.add_trace(go.Scatter(x=x_s, y=y_s, line=dict(color='#3498db', width=4), name="Profilo Lamella"))
        fig_vis.add_trace(go.Scatter(x=[6, 12], y=[0,0], line=dict(color='gray', dash='dot'), name="Pistone"))
        fig_vis.update_layout(height=220, margin=dict(l=20,r=20,t=30,b=20), template="plotly_dark", yaxis_range=[-0.2, 2.0], title=f"Apertura Lamella @ {v_sim} m/s: {lift:.2f}mm")
        st.plotly_chart(fig_vis, use_container_width=True)

# --- TAB 2: MONO ---
with t_shock:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("Stack Compressione")
        st.session_state["shock_comp_df"] = render_stack("shock_comp")
        st.subheader("Stack Ritorno")
        st.session_state["shock_reb_df"] = render_stack("shock_reb")
    
    with c2:
        st.subheader("Simulazione & Cavitazione")
        v_sim_s = st.slider("Velocità Simulazione (m/s)", 0.0, 6.0, 2.0, key="vs")
        
        k_sc = calc_k(st.session_state["shock_comp_df"])
        geo_s = {'d_piston': 50.0, 'd_rod': 16.0, 'type': 'compression', 'n_port': 4, 'w_port': 12.0, 'h_deck': 3.0, 'd_throat': 100}
        
        forces_s = []
        lifts_s = []
        for v in vels:
            f, l = SuspensionPhysics.solve_damping(v, k_sc, geo_s, 1.0, 0)
            forces_s.append(f)
            lifts_s.append(l)
        
        # Plot Curve
        fig_s = go.Figure()
        fig_s.add_trace(go.Scatter(x=vels, y=forces_s, line=dict(color='#e74c3c', width=3), name="Compressione"))
        # Linea limite cavitazione fittizia
        fig_s.add_hline(y=1800, line_dash="dash", line_color="red", annotation_text="Limite Cavitazione")
        fig_s.update_layout(height=250, margin=dict(l=20,r=20,t=30,b=20), template="plotly_dark", title="Curva Mono")
        st.plotly_chart(fig_s, use_container_width=True)
        
        # Plot Visualizer
        idx_s = (np.abs(vels - v_sim_s)).argmin()
        lift_s = lifts_s[idx_s]
        fig_vis_s = go.Figure()
        x_ss = np.linspace(6, 25, 20)
        y_ss = lift_s * ((x_ss-6)/(25-6))**2
        fig_vis_s.add_trace(go.Scatter(x=x_ss, y=y_ss, line=dict(color='#e74c3c', width=4)))
        fig_vis_s.add_trace(go.Scatter(x=[6, 25], y=[0,0], line=dict(color='gray', dash='dot')))
        fig_vis_s.update_layout(height=220, margin=dict(l=20,r=20,t=30,b=20), template="plotly_dark", yaxis_range=[-0.2, 2.5], title=f"Apertura Mono @ {v_sim_s} m/s: {lift_s:.2f}mm")
        st.plotly_chart(fig_vis_s, use_container_width=True)

# --- TAB 3: TELAIO (SAG) ---
with t_chassis:
    st.subheader("⚖️ Calcolatore Bilanciamento & Sag")
    
    col_w1, col_w2 = st.columns(2)
    rider_w_actual = st.session_state.get("rider_weight", 80.0)
    
    with col_w1:
        st.metric("Peso Pilota (Impostato)", f"{rider_w_actual} kg")
    with col_w2:
        target_w = st.number_input("Peso Standard Molla (kg)", 50, 120, 75, help="Il peso per cui la molla attuale è tarata")
        
    # Calcolo suggerimenti
    ratio = rider_w_actual / target_w
    spring_change_pct = (ratio - 1) * 100
    hyd_change_pct = (np.sqrt(ratio) - 1) * 100
    
    st.markdown("#### Analisi Setup")
    c1, c2, c3 = st.columns(3)
    
    c1.info(f"Molla Consigliata: **{spring_change_pct:+.1f}%** Rigidità")
    c2.warning(f"Idraulica Consigliata: **{hyd_change_pct:+.1f}%** Click")
    c3.success("Target Sag: **35mm** (Static) / **105mm** (Rider)")
    
    st.caption("Nota: Il calcolo si basa sulla variazione della frequenza naturale del sistema sospensivo al variare del carico.")
