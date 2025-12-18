import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
from physics import SuspensionPhysics
from db_manager import SuspensionDB

# --- SETUP PAGINA ---
st.set_page_config(layout="wide", page_title="SuspensionLab PRO", page_icon="⚙️")

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1E1E1E; border-radius: 5px; color: white; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #E67E22; color: white; }
    .metric-card { background-color: #262730; padding: 15px; border-radius: 10px; border: 1px solid #444; }
    .warning-cav { background-color: #ff4b4b; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
    div[data-testid="stToast"] { background-color: #2ecc71; color: white; }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---
def init_session_state():
    # Inizializza i dataframe se non esistono (o se resettati)
    defaults = {
        "fork_bv_df": pd.DataFrame([{"qty": 1, "od": 20.0, "th": 0.15}, {"qty": 1, "od": 18.0, "th": 0.15}, {"qty": 1, "od": 12.0, "th": 0.20}]),
        "fork_mv_df": pd.DataFrame([{"qty": 1, "od": 20.0, "th": 0.10}, {"qty": 1, "od": 12.0, "th": 0.20}]),
        "shock_comp_df": pd.DataFrame([{"qty": 1, "od": 40.0, "th": 0.20}, {"qty": 1, "od": 30.0, "th": 0.15}, {"qty": 1, "od": 16.0, "th": 0.30}]),
        "shock_reb_df": pd.DataFrame([{"qty": 1, "od": 36.0, "th": 0.15}, {"qty": 1, "od": 16.0, "th": 0.30}])
    }
    for key, df in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = df

def render_stack_editor(key_prefix):
    # Wrapper per l'editor che usa la session state
    return st.data_editor(
        st.session_state[f"{key_prefix}_df"],
        num_rows="dynamic",
        column_config={
            "qty": st.column_config.NumberColumn("Q.tà", min_value=1, max_value=10, step=1, format="%d"),
            "od": st.column_config.NumberColumn("Ø Est", min_value=6.0, max_value=60.0, step=0.5, format="%.1f"),
            "th": st.column_config.NumberColumn("Spessore", min_value=0.05, max_value=1.0, step=0.01, format="%.2f")
        },
        use_container_width=True,
        key=f"editor_{key_prefix}"
    )

def calc_stack_stiffness_simple(df):
    k = 0.0
    try:
        for _, row in df.iterrows():
            k += (row['th']**3) * row['qty'] * 1000 
    except: pass
    return max(k, 0.1)

# Inizializza lo stato
init_session_state()

# --- SIDEBAR (INPUT & SALVATAGGIO) ---
with st.sidebar:
    st.title("🗜️ SuspensionLab")
    st.caption("Physics v2.5 + Cloud DB")
    
    st.divider()
    st.subheader("📝 Dati Cliente")
    modello = st.text_input("Modello Moto", "KTM 450 SX-F")
    peso_pilota = st.number_input("Peso Pilota (kg)", 50, 120, 80)
    note_txt = st.text_area("Note Lavorazione", height=100)
    
    st.divider()
    # PULSANTE SALVATAGGIO
    if st.button("💾 SALVA PROGETTO SU CLOUD", type="primary"):
        # Raccogliamo i dati complessi (Dataframe -> Dict per JSON)
        fork_data = {
            "bv": st.session_state["fork_bv_df"].to_dict('records'),
            "mv": st.session_state["fork_mv_df"].to_dict('records')
        }
        shock_data = {
            "comp": st.session_state["shock_comp_df"].to_dict('records'),
            "reb": st.session_state["shock_reb_df"].to_dict('records')
        }
        
        with st.spinner("Salvataggio su Google Sheets in corso..."):
            SuspensionDB.save_project(modello, peso_pilota, fork_data, shock_data, note_txt)

# --- TABS PRINCIPALI ---
tab_fork, tab_shock, tab_chassis, tab_db = st.tabs(["🔹 FORCELLA", "🔸 MONO", "⚖️ TELAIO", "🗂️ DATABASE CLIENTI"])

# ==============================================================================
# 1. TAB FORCELLA
# ==============================================================================
with tab_fork:
    col_geom, col_air, col_hyd = st.columns([1, 1, 1.5])
    
    with col_geom:
        st.subheader("📏 Geometria")
        f_type = st.selectbox("Sistema Elastico", ["AIR (Pneumatica)", "COIL (Molla)"], index=0)
        f_travel = st.number_input("Corsa (mm)", 100, 350, 300)
        f_stelo = st.selectbox("Ø Stelo", [32, 34, 35, 36, 48, 49, 50], index=4)
        f_rod = st.number_input("Ø Asta Cartuccia", 8.0, 14.0, 12.0)
    
    with col_air:
        st.subheader("💨 Molla / Aria")
        if f_type == "AIR":
            f_psi = st.number_input("Pressione (PSI)", 40, 200, 145)
            with st.expander("🛠️ Volume Tuning (Token)", expanded=True):
                token_type = st.selectbox("Tipo Token", list(SuspensionPhysics.TOKEN_DB.keys()))
                n_tokens = st.slider("Numero Token", 0, 6, 0)
                st.caption(f"Volume ridotto: -{SuspensionPhysics.TOKEN_DB[token_type]*n_tokens:.1f} cc")
        else:
            f_rate = st.number_input("Rate Molla (N/mm)", 2.0, 15.0, 4.6)
            f_preload_mech = st.number_input("Precarico (mm)", 0, 20, 5)

    with col_hyd:
        st.subheader("💧 Valvole")
        f_piston_diam = st.number_input("Ø Pistone Valvola (mm)", 18.0, 40.0, 24.0)
        tab_bv, tab_mv = st.tabs(["Base Valve", "Mid Valve"])
        with tab_bv:
            st.session_state["fork_bv_df"] = render_stack_editor("fork_bv") # Update session state directly
            c1, c2 = st.columns(2)
            f_hdeck = c1.number_input("h.deck", 0.0, 10.0, 2.0)
            f_dthroat = c2.number_input("Ø Throat", 0.0, 50.0, 20.0)
        with tab_mv:
            st.session_state["fork_mv_df"] = render_stack_editor("fork_mv")
            
    # --- SIMULAZIONE FORCELLA (VISUALIZER) ---
    st.markdown("---")
    c_f_plot, c_f_vis = st.columns([2, 1])
    
    # Calcoli al volo
    k_bv = calc_stack_stiffness_simple(st.session_state["fork_bv_df"])
    geo_f = {'d_piston': f_piston_diam, 'd_rod': f_rod, 'type': 'compression', 'n_port': 4, 'w_port': 8.0, 'h_deck': f_hdeck, 'd_throat': f_dthroat}
    
    vels = np.linspace(0.01, 6.0, 50)
    f_hyd_curve = [SuspensionPhysics.solve_damping(v, k_bv, geo_f, 1.5, 0)[0] for v in vels]
    lifts_f = [SuspensionPhysics.solve_damping(v, k_bv, geo_f, 1.5, 0)[1] for v in vels]
    
    with c_f_plot:
        fig_f = go.Figure()
        fig_f.add_trace(go.Scatter(x=vels, y=f_hyd_curve, mode='lines', line=dict(color='#3498db', width=3), name='Idraulica'))
        fig_f.update_layout(title="Base Valve Damping", height=300, template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_f, use_container_width=True)
        
    with c_f_vis:
        st.markdown("**Visualizer**")
        v_vis_f = st.slider("Speed (m/s)", 0.0, 6.0, 1.0, key="v_vis_f")
        idx_f = (np.abs(vels - v_vis_f)).argmin()
        lift_now = lifts_f[idx_f]
        
        fig_sim_f = go.Figure()
        # Lamella
        x_s = np.linspace(6, f_piston_diam/2, 20)
        y_s = lift_now * ((x_s - 6)/(f_piston_diam/2 - 6))**2
        fig_sim_f.add_trace(go.Scatter(x=x_s, y=y_s, mode='lines', line=dict(color='#3498db', width=4)))
        fig_sim_f.add_trace(go.Scatter(x=[6, f_piston_diam/2], y=[0,0], mode='lines', line=dict(color='gray'))) # Riposo
        fig_sim_f.update_layout(height=250, template="plotly_dark", yaxis_range=[-0.2, 2.0], showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_sim_f, use_container_width=True)

# ==============================================================================
# 2. TAB MONO
# ==============================================================================
with tab_shock:
    c_s1, c_s2, c_s3 = st.columns([1, 1, 1.5])
    
    with c_s1:
        st.subheader("Geometria")
        s_piston = st.number_input("Ø Pistone", 36, 50, 50)
        s_rod = st.number_input("Ø Asta", 14, 18, 16)
        s_pres = st.number_input("Bar Azoto", 5.0, 20.0, 10.0)
    
    with c_s2:
        st.subheader("Registro")
        max_clicks = st.number_input("Click Totali", 10, 40, 24)
        click_val = st.slider("Clicker", 0, max_clicks, 12)
        fixed_bleed = st.number_input("Foro Fisso (mm)", 0.0, 3.0, 0.0)
    
    with c_s3:
        st.subheader("Stack")
        st.markdown("**Comp**")
        st.session_state["shock_comp_df"] = render_stack_editor("shock_comp")
        st.markdown("**Reb**")
        st.session_state["shock_reb_df"] = render_stack_editor("shock_reb")

    # --- SIMULAZIONE MONO ---
    st.markdown("---")
    c_s_plot, c_s_vis = st.columns([2, 1])
    
    # Calcoli
    k_sc = calc_stack_stiffness_simple(st.session_state["shock_comp_df"])
    geo_s = {'d_piston': s_piston, 'd_rod': s_rod, 'type': 'compression', 'n_port': 4, 'w_port': 12, 'h_deck': 3.0, 'd_throat': 100}
    
    bleed_area = 3.0 * (click_val/max_clicks)
    f_shock = [SuspensionPhysics.solve_damping(v, k_sc, geo_s, bleed_area, 0)[0] for v in vels]
    lifts_s = [SuspensionPhysics.solve_damping(v, k_sc, geo_s, bleed_area, 0)[1] for v in vels]
    cav_lim = SuspensionPhysics.calc_cavitation_limit(s_pres, s_rod, s_piston)
    
    with c_s_plot:
        fig_s = go.Figure()
        fig_s.add_trace(go.Scatter(x=vels, y=f_shock, mode='lines', line=dict(color='#E74C3C', width=3), name='Comp'))
        fig_s.add_hline(y=cav_lim, line_dash="dash", line_color="red", annotation_text="CAVITAZIONE")
        fig_s.update_layout(title="Shock Comp & Cavitation", height=300, template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_s, use_container_width=True)
        
    with c_s_vis:
        st.markdown("**Visualizer**")
        v_vis_s = st.slider("Speed (m/s)", 0.0, 6.0, 1.0, key="v_vis_s")
        idx_s = (np.abs(vels - v_vis_s)).argmin()
        lift_s_now = lifts_s[idx_s]
        
        fig_sim_s = go.Figure()
        x_ss = np.linspace(6, s_piston/2, 20)
        y_ss = lift_s_now * ((x_ss - 6)/(s_piston/2 - 6))**2
        fig_sim_s.add_trace(go.Scatter(x=x_ss, y=y_ss, mode='lines', line=dict(color='#E74C3C', width=4)))
        fig_sim_s.add_trace(go.Scatter(x=[6, s_piston/2], y=[0,0], mode='lines', line=dict(color='gray')))
        fig_sim_s.update_layout(height=250, template="plotly_dark", yaxis_range=[-0.2, 2.5], showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_sim_s, use_container_width=True)

# ==============================================================================
# 3. TAB TELAIO
# ==============================================================================
with tab_chassis:
    st.subheader("Analisi Peso")
    ratio = st.number_input("Peso Target", 50, 120, 90) / peso_pilota
    st.info(f"Variazione Molla: {ratio:.2f}x | Variazione Idraulica: +{(np.sqrt(ratio)-1)*100:.1f}%")

# ==============================================================================
# 4. TAB DATABASE CLIENTI (LA PARTE MANCANTE)
# ==============================================================================
with tab_db:
    st.subheader("🗂️ Archivio Lavorazioni (Google Sheets)")
    
    # 1. Carica lista progetti
    if st.button("🔄 Aggiorna Lista"):
        st.cache_data.clear() # Forza refresh dati
        
    df_projects = SuspensionDB.load_projects()
    
    if df_projects.empty:
        st.warning("Nessun progetto trovato o Database vuoto.")
    else:
        # Mostra tabella selezionabile
        st.dataframe(
            df_projects[["date", "model", "rider_weight", "notes"]],
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        st.write("#### 📂 Azioni Progetto")
        
        # Selectbox per scegliere quale caricare
        # Creiamo una label leggibile: "Data - Modello (Peso)"
        options = df_projects.apply(lambda x: f"{x['date']} | {x['model']} ({x['rider_weight']}kg)", axis=1).tolist()
        selected_option = st.selectbox("Seleziona Progetto da Caricare/Eliminare:", options)
        
        if selected_option:
            # Trova l'ID corrispondente
            idx = options.index(selected_option)
            row = df_projects.iloc[idx]
            
            c_load, c_del = st.columns(2)
            
            with c_load:
                if st.button("📂 CARICA NEL SIMULATORE", type="primary"):
                    try:
                        # Parsing JSON
                        f_data = SuspensionDB.parse_config(row['fork_data'])
                        s_data = SuspensionDB.parse_config(row['shock_data'])
                        
                        # Aggiornamento Session State (Stack)
                        if 'bv' in f_data: st.session_state["fork_bv_df"] = pd.DataFrame(f_data['bv'])
                        if 'mv' in f_data: st.session_state["fork_mv_df"] = pd.DataFrame(f_data['mv'])
                        if 'comp' in s_data: st.session_state["shock_comp_df"] = pd.DataFrame(s_data['comp'])
                        if 'reb' in s_data: st.session_state["shock_reb_df"] = pd.DataFrame(s_data['reb'])
                        
                        st.success(f"Caricato setup di: {row['model']}")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"Errore nel caricamento dati: {e}")

            with c_del:
                if st.button("🗑️ ELIMINA PER SEMPRE"):
                    SuspensionDB.delete_project(row['id'])
