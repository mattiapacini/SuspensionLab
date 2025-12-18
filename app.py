import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
from physics import SuspensionPhysics
from db_manager import SuspensionDB

# --- 1. CONFIGURAZIONE PAGINA E STILE ---
st.set_page_config(layout="wide", page_title="SuspensionLab PRO", page_icon="⚙️")

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1E1E1E; border-radius: 5px; color: white; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #E67E22; color: white; }
    .stButton button { width: 100%; border-radius: 5px; font-weight: bold; }
    div[data-testid="stToast"] { background-color: #2ecc71; color: white; }
    hr { margin: 15px 0; border-color: #444; }
</style>
""", unsafe_allow_html=True)

# --- 2. INIZIALIZZAZIONE STATO (Session State) ---
def init_session_state():
    """Inizializza le variabili se non esistono, per evitare crash al primo avvio."""
    defaults = {
        "fork_bv_df": pd.DataFrame([{"qty": 1, "od": 20.0, "th": 0.15}, {"qty": 1, "od": 18.0, "th": 0.15}, {"qty": 1, "od": 12.0, "th": 0.20}]),
        "fork_mv_df": pd.DataFrame([{"qty": 1, "od": 20.0, "th": 0.10}, {"qty": 1, "od": 12.0, "th": 0.20}]),
        "shock_comp_df": pd.DataFrame([{"qty": 1, "od": 40.0, "th": 0.20}, {"qty": 1, "od": 30.0, "th": 0.15}, {"qty": 1, "od": 16.0, "th": 0.30}]),
        "shock_reb_df": pd.DataFrame([{"qty": 1, "od": 36.0, "th": 0.15}, {"qty": 1, "od": 16.0, "th": 0.30}]),
        "model": "KTM 450 SX-F",
        "rider_weight": 80,
        "notes": ""
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# --- 3. FUNZIONI HELPER ---
def render_stack_editor(key_prefix):
    """Crea la tabella editabile per le lamelle."""
    return st.data_editor(
        st.session_state[f"{key_prefix}_df"],
        num_rows="dynamic",
        column_config={
            "qty": st.column_config.NumberColumn("Q.tà", min_value=1, max_value=20, step=1, format="%d"),
            "od": st.column_config.NumberColumn("Ø Est (mm)", min_value=6.0, max_value=60.0, step=0.5, format="%.1f"),
            "th": st.column_config.NumberColumn("Spessore", min_value=0.05, max_value=1.0, step=0.01, format="%.2f")
        },
        use_container_width=True,
        key=f"editor_{key_prefix}"
    )

def calc_k_simple(df):
    """Calcolo rapido rigidezza stack per UI."""
    k = 0.0
    try:
        for _, row in df.iterrows():
            k += (row['th']**3) * row['qty'] * 1000
    except: pass
    return max(k, 0.1)

# ==============================================================================
# SIDEBAR: GESTIONE COMPLETA DATABASE (Google Sheets)
# ==============================================================================
with st.sidebar:
    st.title("🗜️ SuspensionLab")
    st.caption("Pro Version | GSheets Connected")
    
    # --- SEZIONE CARICAMENTO ---
    st.markdown("### 📂 Archivio Clienti")
    
    # Carica dati dal DB Manager
    df_projects = SuspensionDB.load_projects()
    
    if not df_projects.empty:
        # Crea lista leggibile
        options = df_projects.apply(lambda x: f"{x['date']} | {x['model']} ({x['rider_weight']}kg)", axis=1).tolist()
        selected_proj_str = st.selectbox("Seleziona Setup:", options, label_visibility="collapsed")
        
        c1, c2 = st.columns(2)
        
        # BOTTONE CARICA
        if c1.button("📂 CARICA", use_container_width=True):
            try:
                idx = options.index(selected_proj_str)
                row = df_projects.iloc[idx]
                
                # Parsing JSON
                f_data = SuspensionDB.parse_config(row['fork_data'])
                s_data = SuspensionDB.parse_config(row['shock_data'])
                
                # Aggiorna Session State
                st.session_state["model"] = row['model']
                st.session_state["rider_weight"] = row['rider_weight']
                st.session_state["notes"] = row['notes']
                
                if 'bv' in f_data: st.session_state["fork_bv_df"] = pd.DataFrame(f_data['bv'])
                if 'mv' in f_data: st.session_state["fork_mv_df"] = pd.DataFrame(f_data['mv'])
                if 'comp' in s_data: st.session_state["shock_comp_df"] = pd.DataFrame(s_data['comp'])
                if 'reb' in s_data: st.session_state["shock_reb_df"] = pd.DataFrame(s_data['reb'])
                
                st.toast(f"Caricato: {row['model']}", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Errore caricamento: {e}")

        # BOTTONE ELIMINA
        if c2.button("🗑️ ELIMINA", use_container_width=True):
            idx = options.index(selected_proj_str)
            proj_id = df_projects.iloc[idx]['id']
            SuspensionDB.delete_project(proj_id)
            
    else:
        st.info("Database vuoto o non connesso.")

    st.markdown("---")
    
    # --- SEZIONE SALVATAGGIO ---
    st.markdown("### 📝 Setup Corrente")
    
    # Input diretti su Session State
    modello = st.text_input("Modello Moto", value=st.session_state["model"], key="input_model")
    peso = st.number_input("Peso Pilota (kg)", value=st.session_state["rider_weight"], key="input_weight")
    note = st.text_area("Note Lavorazione", value=st.session_state["notes"], height=100, key="input_notes")
    
    # BOTTONE SALVA
    if st.button("💾 SALVA SU CLOUD", type="primary", use_container_width=True):
        f_data_export = {
            "bv": st.session_state["fork_bv_df"].to_dict('records'),
            "mv": st.session_state["fork_mv_df"].to_dict('records')
        }
        s_data_export = {
            "comp": st.session_state["shock_comp_df"].to_dict('records'),
            "reb": st.session_state["shock_reb_df"].to_dict('records')
        }
        
        with st.spinner("Salvataggio su Google Sheets in corso..."):
            SuspensionDB.save_project(modello, peso, f_data_export, s_data_export, note)

# ==============================================================================
# MAIN PAGE: SIMULATORE COMPLETO
# ==============================================================================

tab_fork, tab_shock, tab_chassis = st.tabs(["🔹 FORCELLA (Front)", "🔸 MONO (Rear)", "⚖️ TELAIO"])

# ------------------------------------------------------------------------------
# TAB 1: FORCELLA
# ------------------------------------------------------------------------------
with tab_fork:
    col_geom, col_hyd = st.columns([1, 1.5])
    
    # INPUT GEOMETRIA
    with col_geom:
        st.subheader("📏 Geometria & Molla")
        f_type = st.selectbox("Sistema", ["AIR (Pneumatica)", "COIL (Molla)"])
        
        c_g1, c_g2 = st.columns(2)
        f_travel = c_g1.number_input("Corsa (mm)", 100, 350, 300)
        f_stelo = c_g2.selectbox("Ø Stelo", [35, 36, 48, 49, 50], index=2)
        f_rod = st.number_input("Ø Asta Cartuccia (mm)", 8.0, 14.0, 12.0)
        
        if f_type.startswith("AIR"):
            f_psi = st.number_input("Pressione (PSI)", 40, 200, 145)
            st.caption("Volume Token non attivo in questa versione")
        else:
            f_rate = st.number_input("K Molla (N/mm)", 2.0, 15.0, 4.6)

        st.markdown("---")
        st.subheader("🥞 Stack Base Valve (Comp)")
        st.session_state["fork_bv_df"] = render_stack_editor("fork_bv")
        
        st.subheader("🥞 Stack Mid Valve")
        st.session_state["fork_mv_df"] = render_stack_editor("fork_mv")

    # SIMULATORE FORCELLA
    with col_hyd:
        st.subheader("🧪 Simulazione Idraulica")
        
        # Parametri Simulazione
        c_p1, c_p2 = st.columns(2)
        f_piston = c_p1.number_input("Ø Pistone Valvola", 18.0, 40.0, 24.0)
        v_sim_f = c_p2.slider("Velocità Visualizer (m/s)", 0.0, 6.0, 2.0)
        
        # 1. Calcolo Fisica
        k_bv = calc_k_simple(st.session_state["fork_bv_df"])
        geo_f = {'d_piston': f_piston, 'd_rod': f_rod, 'type': 'compression', 'n_port': 4, 'w_port': 8.0, 'h_deck': 2.0, 'd_throat': 20.0}
        
        vels = np.linspace(0.01, 6.0, 50)
        f_curve = []
        lifts_f = []
        
        for v in vels:
            # Simuliamo clicker aperto a 1.5mm2
            force, lift = SuspensionPhysics.solve_damping(v, k_bv, geo_f, 1.5, 0)
            f_curve.append(force)
            lifts_f.append(lift)
            
        # 2. Grafico Forza
        fig_f = go.Figure()
        fig_f.add_trace(go.Scatter(x=vels, y=f_curve, mode='lines', line=dict(color='#3498db', width=3), name='Idraulica'))
        fig_f.add_vrect(x0=0, x1=0.3, fillcolor="green", opacity=0.1, annotation_text="LSC")
        fig_f.update_layout(title="Curva Smorzamento (Damping)", xaxis_title="m/s", yaxis_title="Forza (N)", height=280, template="plotly_dark", margin=dict(l=20,r=20,t=40,b=20))
        st.plotly_chart(fig_f, use_container_width=True)
        
        # 3. Visualizer Lamella
        st.markdown("#### 👁️ Flessione Reale")
        idx_f = (np.abs(vels - v_sim_f)).argmin()
        lift_now_f = lifts_f[idx_f]
        
        fig_vis_f = go.Figure()
        r_start = 6.0
        r_end = f_piston / 2
        
        # Curva deformata
        x_s = np.linspace(r_start, r_end, 20)
        y_s = lift_now_f * ((x_s - r_start)/(r_end - r_start))**2
        
        fig_vis_f.add_trace(go.Scatter(x=x_s, y=y_s, mode='lines', line=dict(color='#3498db', width=4), name="Deformata"))
        fig_vis_f.add_trace(go.Scatter(x=[r_start, r_end], y=[0,0], mode='lines', line=dict(color='gray', dash='dot'), name="Riposo"))
        
        # Pistone grafico
        fig_vis_f.add_trace(go.Scatter(x=[r_end, r_end+2], y=[0,0], mode='lines', line=dict(color='white', width=5)))

        fig_vis_f.update_layout(
            title=f"Apertura: {lift_now_f:.2f}mm @ {v_sim_f}m/s",
            yaxis_range=[-0.2, 2.0], xaxis_title="Raggio (mm)",
            height=250, template="plotly_dark", showlegend=False,
            margin=dict(l=20,r=20,t=40,b=20)
        )
        st.plotly_chart(fig_vis_f, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: MONO
# ------------------------------------------------------------------------------
with tab_shock:
    col_s_geom, col_s_hyd = st.columns([1, 1.5])
    
    # INPUT MONO
    with col_s_geom:
        st.subheader("📏 Geometria Mono")
        s_piston = st.number_input("Ø Pistone (mm)", 36, 50, 50)
        s_rod = st.number_input("Ø Asta (mm)", 14, 18, 16)
        s_pres = st.number_input("Pressione Gas (Bar)", 5.0, 20.0, 10.0)
        
        st.markdown("---")
        st.subheader("🥞 Stack Compressione")
        st.session_state["shock_comp_df"] = render_stack_editor("shock_comp")
        
        st.subheader("🥞 Stack Ritorno")
        st.session_state["shock_reb_df"] = render_stack_editor("shock_reb")

    # SIMULATORE MONO
    with col_s_hyd:
        st.subheader("🧪 Simulazione & Cavitazione")
        
        c_k1, c_k2, c_k3 = st.columns(3)
        max_clicks = c_k1.number_input("Click Max", 10, 40, 24)
        click_pos = c_k2.slider("Clicker (Aperti)", 0, int(max_clicks), 12)
        v_sim_s = c_k3.slider("Velocità Vis", 0.0, 6.0, 2.0)
        
        # 1. Calcolo Fisica
        k_sc = calc_k_simple(st.session_state["shock_comp_df"])
        geo_s = {'d_piston': s_piston, 'd_rod': s_rod, 'type': 'compression', 'n_port': 4, 'w_port': 12, 'h_deck': 3.0, 'd_throat': 100}
        
        bleed_area = 3.0 * (click_pos / max_clicks)
        cav_limit = SuspensionPhysics.calc_cavitation_limit(s_pres, s_rod, s_piston)
        
        s_curve = []
        lifts_s = []
        
        for v in vels:
            f, l = SuspensionPhysics.solve_damping(v, k_sc, geo_s, bleed_area, 0)
            s_curve.append(f)
            lifts_s.append(l)
            
        # 2. Grafico Forza + Cavitazione
        fig_s = go.Figure()
        fig_s.add_trace(go.Scatter(x=vels, y=s_curve, mode='lines', line=dict(color='#e74c3c', width=3), name='Compressione'))
        fig_s.add_hline(y=cav_limit, line_dash="dash", line_color="red", annotation_text="CAVITAZIONE")
        
        # Check allarme
        if max(s_curve) > cav_limit:
            st.error(f"⚠️ ALLARME: La forza ({max(s_curve):.0f}N) supera il limite di cavitazione ({cav_limit:.0f}N)!")
            
        fig_s.update_layout(title="Curva Compressione", xaxis_title="m/s", yaxis_title="Forza (N)", height=280, template="plotly_dark", margin=dict(l=20,r=20,t=40,b=20))
        st.plotly_chart(fig_s, use_container_width=True)
        
        # 3. Visualizer Lamella Mono
        st.markdown("#### 👁️ Flessione Mono")
        idx_s = (np.abs(vels - v_sim_s)).argmin()
        lift_now_s = lifts_s[idx_s]
        
        fig_vis_s = go.Figure()
        r_end_s = s_piston / 2
        
        x_ss = np.linspace(6.0, r_end_s, 20)
        y_ss = lift_now_s * ((x_ss - 6.0)/(r_end_s - 6.0))**2
        
        fig_vis_s.add_trace(go.Scatter(x=x_ss, y=y_ss, mode='lines', line=dict(color='#e74c3c', width=4)))
        fig_vis_s.add_trace(go.Scatter(x=[6.0, r_end_s], y=[0,0], mode='lines', line=dict(color='gray', dash='dot')))
        fig_vis_s.add_trace(go.Scatter(x=[r_end_s, r_end_s+3], y=[0,0], mode='lines', line=dict(color='white', width=5)))
        
        fig_vis_s.update_layout(
            title=f"Apertura: {lift_now_s:.2f}mm @ {v_sim_s}m/s",
            yaxis_range=[-0.2, 2.5], xaxis_title="Raggio (mm)",
            height=250, template="plotly_dark", showlegend=False,
            margin=dict(l=20,r=20,t=40,b=20)
        )
        st.plotly_chart(fig_vis_s, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 3: TELAIO
# ------------------------------------------------------------------------------
with tab_chassis:
    st.subheader("⚖️ Analisi Bilanciamento")
    
    target_w = st.number_input("Peso Target Pilota (kg)", 50, 120, 90)
    current_w = st.session_state["rider_weight"]
    
    ratio = target_w / current_w if current_w > 0 else 1.0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Variazione Peso", f"{((ratio-1)*100):.1f}%")
    c2.metric("Molla Richiesta", f"{ratio:.2f}x")
    c3.metric("Idraulica (+/-)", f"{((np.sqrt(ratio)-1)*100):.1f}%")
    
    st.info("I calcoli si basano sulla variazione proporzionale di energia cinetica e frequenza naturale.")
