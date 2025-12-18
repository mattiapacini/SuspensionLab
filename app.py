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
    div[data-testid="stExpander"] { background-color: #262730; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- INIT STATE ---
if "init_done" not in st.session_state:
    # Dati di default per evitare tabelle vuote
    default_bv = [{"qty": 5, "od": 20.0, "th": 0.15}, {"qty": 1, "od": 18.0, "th": 0.10}]
    default_mv = [{"qty": 3, "od": 20.0, "th": 0.10}]
    default_s_comp = [{"qty": 8, "od": 40.0, "th": 0.20}, {"qty": 1, "od": 30.0, "th": 0.15}]
    default_s_reb = [{"qty": 4, "od": 36.0, "th": 0.15}]

    st.session_state.update({
        "fork_bv_df": pd.DataFrame(default_bv),
        "fork_mv_df": pd.DataFrame(default_mv),
        "shock_comp_df": pd.DataFrame(default_s_comp),
        "shock_reb_df": pd.DataFrame(default_s_reb),
        "current_pilot_id": None,
        "current_bike_id": None,
        "rider_weight": 80.0,
        "init_done": True
    })

# --- HELPER FUNCTIONS ---
def render_stack(key, title):
    """Renderizza la tabella editabile per gli spessori con un titolo chiaro"""
    st.markdown(f"**{title}**")
    return st.data_editor(
        st.session_state[f"{key}_df"],
        num_rows="dynamic",
        column_config={
            "qty": st.column_config.NumberColumn("Q.tà", min_value=1, max_value=50, step=1, format="%d"),
            "od": st.column_config.NumberColumn("Ø Est", min_value=6.0, max_value=60.0, step=0.5, format="%.1f"),
            "th": st.column_config.NumberColumn("Spess", min_value=0.05, max_value=1.0, step=0.01, format="%.2f")
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
    opts_piloti = ["➕ NUOVO PILOTA"] 
    if not df_piloti.empty:
        opts_piloti += df_piloti.apply(lambda x: f"{x['Nome']} (ID:{x['ID']})", axis=1).tolist()
    
    sel_pilota = st.selectbox("👤 Pilota", opts_piloti)
    
    if sel_pilota == "➕ NUOVO PILOTA":
        with st.form("new_pilot"):
            n_nome = st.text_input("Nome")
            n_peso = st.number_input("Peso (kg)", 50, 120, 80)
            n_liv = st.selectbox("Livello", ["Amatore", "Pro"])
            if st.form_submit_button("Crea"):
                SuspensionDB.add_pilota(n_nome, n_peso, n_liv, "", "")
                st.rerun()
        st.stop()
    else:
        try:
            pid_idx = opts_piloti.index(sel_pilota) - 1
            st.session_state["current_pilot_id"] = df_piloti.iloc[pid_idx]["ID"]
        except: pass

    st.markdown("---")

    # 2. MOTO
    if st.session_state["current_pilot_id"]:
        df_garage = SuspensionDB.get_garage(st.session_state["current_pilot_id"])
        opts_moto = ["➕ AGGIUNGI MOTO"]
        if not df_garage.empty:
            opts_moto += df_garage.apply(lambda x: f"{x['marca']} {x['modello']}", axis=1).tolist()
            
        sel_moto = st.selectbox("🏍️ Garage", opts_moto)
        
        if sel_moto == "➕ AGGIUNGI MOTO":
            with st.form("new_moto"):
                ma = st.text_input("Marca")
                mo = st.text_input("Modello")
                an = st.number_input("Anno", 2000, 2025, 2024)
                if st.form_submit_button("Crea"):
                    SuspensionDB.add_mezzo(st.session_state["current_pilot_id"], "Cross", ma, mo, an, "", "")
                    st.rerun()
            st.stop()
        else:
            try:
                mid_idx = opts_moto.index(sel_moto) - 1
                st.session_state["current_bike_id"] = df_garage.iloc[mid_idx]["id_mezzo"]
            except: pass

            # 3. SESSIONI
            st.markdown("---")
            st.write("📂 **Gestione Sessioni**")
            df_sess = SuspensionDB.get_sessioni(st.session_state["current_bike_id"])
            if not df_sess.empty:
                opts_sess = df_sess.apply(lambda x: f"{x['data']} | {x['pista_luogo']}", axis=1).tolist()
                sel_sess = st.selectbox("Storico:", opts_sess)
                if st.button("CARICA DATI", use_container_width=True):
                    row = df_sess.iloc[opts_sess.index(sel_sess)]
                    tech = SuspensionDB.parse_json(row['dati_tecnici_json'])
                    # Caricamento sicuro
                    for k in ['f_bv', 'f_mv', 's_comp', 's_reb']:
                        if k in tech: 
                            key_map = {'f_bv':'fork_bv', 'f_mv':'fork_mv', 's_comp':'shock_comp', 's_reb':'shock_reb'}
                            st.session_state[f"{key_map[k]}_df"] = pd.DataFrame(tech[k])
                    st.toast("Setup caricato!")
                    st.rerun()

            with st.expander("💾 Salva Attuale"):
                pista = st.text_input("Pista")
                cond = st.selectbox("Condizione", ["Secco", "Fango", "Sabbia"])
                note = st.text_area("Note")
                if st.button("SALVA"):
                    pack = {
                        "f_bv": st.session_state["fork_bv_df"].to_dict('records'),
                        "f_mv": st.session_state["fork_mv_df"].to_dict('records'),
                        "s_comp": st.session_state["shock_comp_df"].to_dict('records'),
                        "s_reb": st.session_state["shock_reb_df"].to_dict('records')
                    }
                    SuspensionDB.save_session(st.session_state["current_bike_id"], pista, cond, note, 3, pack)

# ==============================================================================
# MAIN: SIMULATORE COMPLETO
# ==============================================================================

if not st.session_state.get("current_bike_id"):
    st.info("👈 Seleziona Pilota e Moto per iniziare.")
    st.stop()

# Tabs
t1, t2, t3 = st.tabs(["🔹 FORCELLA", "🔸 MONO", "⚖️ TELAIO"])

# --- TAB 1: FORCELLA ---
with t1:
    col_setup, col_sim = st.columns([1, 1.2])
    
    with col_setup:
        st.subheader("🛠️ Taratura")
        st.session_state["fork_bv_df"] = render_stack("fork_bv", "Base Valve (BV)")
        st.divider()
        st.session_state["fork_mv_df"] = render_stack("fork_mv", "Mid Valve (MV)")
        
    with col_sim:
        st.subheader("📐 Geometria & Simulazione")
        
        # --- INSERIMENTO GEOMETRIA FORCELLA ---
        with st.expander("📏 Geometria Idraulica (Modificabile)", expanded=True):
            cg1, cg2 = st.columns(2)
            f_d_piston = cg1.number_input("Ø Pistone (mm)", 20.0, 50.0, 24.0, key="f_dp")
            f_d_rod = cg2.number_input("Ø Asta (mm)", 8.0, 20.0, 12.0, key="f_dr")
            cg3, cg4 = st.columns(2)
            f_n_port = cg3.number_input("N° Port", 2, 6, 4, key="f_np")
            f_w_port = cg4.number_input("Largh. Port (mm)", 2.0, 15.0, 8.0, key="f_wp")
        
        # Slider velocità
        v_sim = st.slider("Velocità Simulazione (m/s)", 0.0, 8.0, 2.0, 0.1)

        # Calcolo Fisica
        k_bv = calc_k(st.session_state["fork_bv_df"])
        geo_f = {'d_piston': f_d_piston, 'd_rod': f_d_rod, 'type': 'compression', 'n_port': int(f_n_port), 'w_port': f_w_port, 'h_deck': 2.0, 'd_throat': 20.0}
        
        vels = np.linspace(0.01, 8.0, 50)
        forces = []
        lifts = []
        for v in vels:
            f, l = SuspensionPhysics.solve_damping(v, k_bv, geo_f, 1.5, 0)
            forces.append(f)
            lifts.append(l)

        # GRAFICO
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=vels, y=forces, line=dict(color='#3498db', width=3), name="Damping"))
        fig.update_layout(height=250, margin=dict(l=20,r=20,t=10,b=20), template="plotly_dark", title="Curva Forza / Velocità")
        st.plotly_chart(fig, use_container_width=True)
        
        # VISUALIZER LAMELLA
        idx = (np.abs(vels - v_sim)).argmin()
        lift = lifts[idx]
        fig_vis = go.Figure()
        x_s = np.linspace(6, f_d_piston/2, 20)
        y_s = lift * ((x_s-6)/((f_d_piston/2)-6))**2
        fig_vis.add_trace(go.Scatter(x=x_s, y=y_s, line=dict(color='#3498db', width=4), fill='tozeroy'))
        fig_vis.update_layout(height=180, margin=dict(l=20,r=20,t=30,b=20), template="plotly_dark", yaxis_range=[0, 2.0], title=f"Deflessione Lamella: {lift:.2f}mm")
        st.plotly_chart(fig_vis, use_container_width=True)

# --- TAB 2: MONO ---
with t2:
    col_setup_s, col_sim_s = st.columns([1, 1.2])
    
    with col_setup_s:
        st.subheader("🛠️ Taratura Mono")
        st.session_state["shock_comp_df"] = render_stack("shock_comp", "Compressione")
        st.divider()
        st.session_state["shock_reb_df"] = render_stack("shock_reb", "Ritorno")
        
    with col_sim_s:
        st.subheader("📐 Geometria Mono")
        
        # --- INSERIMENTO GEOMETRIA MONO ---
        with st.expander("📏 Geometria Idraulica (Modificabile)", expanded=True):
            sg1, sg2 = st.columns(2)
            s_d_piston = sg1.number_input("Ø Pistone (mm)", 30.0, 60.0, 50.0, key="s_dp")
            s_d_rod = sg2.number_input("Ø Asta (mm)", 10.0, 20.0, 16.0, key="s_dr")
            sg3, sg4 = st.columns(2)
            s_n_port = sg3.number_input("N° Port", 2, 6, 4, key="s_np")
            s_w_port = sg4.number_input("Largh. Port (mm)", 5.0, 20.0, 12.0, key="s_wp")

        k_sc = calc_k(st.session_state["shock_comp_df"])
        geo_s = {'d_piston': s_d_piston, 'd_rod': s_d_rod, 'type': 'compression', 'n_port': int(s_n_port), 'w_port': s_w_port, 'h_deck': 3.0, 'd_throat': 100}
        
        vels_s = np.linspace(0.01, 6.0, 50)
        forces_s = []
        for v in vels_s:
            f, _ = SuspensionPhysics.solve_damping(v, k_sc, geo_s, 1.0, 0)
            forces_s.append(f)
            
        fig_s = go.Figure()
        fig_s.add_trace(go.Scatter(x=vels_s, y=forces_s, line=dict(color='#e74c3c', width=3)))
        fig_s.update_layout(height=300, margin=dict(l=20,r=20,t=10,b=20), template="plotly_dark", title="Curva Compressione Mono")
        st.plotly_chart(fig_s, use_container_width=True)

# --- TAB 3: TELAIO ---
with t3:
    st.subheader("⚖️ Calcolo SAG e Molle")
    rw = st.number_input("Peso Pilota (Vestito)", value=80.0)
    tw = st.number_input("Peso Standard Molla", value=75.0)
    
    diff = (rw - tw) / tw * 100
    st.metric("Variazione Richiesta Molla", f"{diff:+.1f}%", delta_color="inverse")
    
    if diff > 5:
        st.warning("⚠️ Serve una molla più dura.")
    elif diff < -5:
        st.warning("⚠️ Serve una molla più morbida.")
    else:
        st.success("✅ La molla standard è corretta.")
