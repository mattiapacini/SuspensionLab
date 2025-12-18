import streamlit as st
import pandas as pd
import numpy as np
import json
import time
import matplotlib.pyplot as plt
from streamlit_gsheets import GSheetsConnection

# --- IMPORT MODULI ---
try:
    from db_manager import SuspensionDB
    from physics import SuspensionPhysics
except ImportError:
    st.error("⚠️ ERRORE: Carica prima db_manager.py e physics.py")
    st.stop()

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="SuspensionLab", page_icon="🔧", layout="wide")

# --- CSS DARK ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1a1c24; border-right: 1px solid #333; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    h1, h2, h3 { color: #1a1c24; }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONE GRAFICA ---
def plot_shim_bending(k_factor, stack, d_clamp, d_piston, geo_data):
    if not stack: return None
    max_od = max([float(x['od']) for x in stack])
    speeds = [0.5, 2.0, 6.0]
    colors = ['#27ae60', '#f39c12', '#c0392b']
    
    df_sim = SuspensionPhysics.simulate_damping_curve(k_factor, geo_data)
    fig, ax = plt.subplots(figsize=(8, 3.5))
    
    r_clamp = d_clamp / 2.0
    r_piston = d_piston / 2.0
    r_port = geo_data['r_port']
    
    ax.plot([0, r_piston], [0, 0], color='#2c3e50', linewidth=3)
    ax.fill_between([0, r_clamp], [0, 0], [0.5, 0.5], color='#34495e')
    ax.axvline(x=r_port, color='gray', linestyle='--')

    for i, v in enumerate(speeds):
        row = df_sim.iloc[(df_sim['Velocità (m/s)'] - v).abs().argsort()[:1]]
        y_max = row['Lift (mm)'].values[0]
        radii, deflections = SuspensionPhysics.get_shim_profile(k_factor, d_clamp, max_od, y_max)
        ax.plot(radii, deflections, color=colors[i], label=f'{v} m/s')
        ax.fill_between(radii, deflections, 0, color=colors[i], alpha=0.1)

    ax.set_ylim(-0.5, 2.5)
    ax.legend()
    return fig

# --- LOGIN ---
if "autenticato" not in st.session_state: st.session_state["autenticato"] = False
if not st.session_state["autenticato"]:
    pwd = st.text_input("Password", type="password")
    if st.button("ENTRA"):
        if pwd == "sospensioni2025":
            st.session_state["autenticato"] = True
            st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    try: lista_piloti = SuspensionDB.get_piloti_options()
    except: lista_piloti = []
    
    pilota_sel = st.selectbox("PILOTA", ["Seleziona..."] + lista_piloti)
    mezzo_sel = None
    if pilota_sel != "Seleziona...":
        id_p = pilota_sel.split("(")[-1].replace(")", "")
        mezzo_sel = st.selectbox("MEZZO", ["Nuovo..."] + SuspensionDB.get_mezzi_by_pilota(id_p))
    
    st.markdown("---")
    with st.expander("Nuovo Pilota"):
        with st.form("np"):
            n = st.text_input("Nome")
            if st.form_submit_button("Salva") and n:
                SuspensionDB.add_pilota(n, 75, "Amatore", "", "")
                st.rerun()

# --- MAIN ---
if mezzo_sel and mezzo_sel != "Nuovo...":
    st.title(f"🛠️ {mezzo_sel.split('(')[0]}")
    t1, t2, t3, t4 = st.tabs(["SETUP", "SIMULATORE", "DIARIO", "STORICO"])
    
    with t1:
        st.info("Setup Base")
        st.number_input("Molla", 4.0, 6.0, 4.6)
        
    with t2:
        c_geo, c_stack, c_res = st.columns([1, 1, 2])
        with c_geo:
            d_p = st.number_input("Ø Pistone", value=50.0)
            r_p = st.number_input("r.port", value=12.0)
            geo = {"d_piston": d_p, "r_port": r_p, "w_port": 8.0, "n_ports": 4, "d_rod": 16.0}
            
        with c_stack:
            d_c = st.number_input("Ø Clamp", value=12.0)
            if "stack" not in st.session_state: st.session_state["stack"] = []
            c1, c2, c3 = st.columns(3)
            q = c1.number_input("Q", 1, 10, 1)
            od = c2.number_input("OD", 6.0, 44.0, 30.0)
            th = c3.selectbox("Th", [0.1, 0.15, 0.2, 0.25, 0.3])
            if st.button("Add"): st.session_state["stack"].append({"qty":q, "od":od, "th":th})
            st.dataframe(pd.DataFrame(st.session_state["stack"]), hide_index=True)
            if st.button("Reset"): st.session_state["stack"]=[]; st.rerun()
            
        with c_res:
            if st.button("CALCOLA", type="primary"):
                if st.session_state["stack"]:
                    k = SuspensionPhysics.calculate_stiffness_factor(st.session_state["stack"], d_c, d_p)
                    df = SuspensionPhysics.simulate_damping_curve(k, geo)
                    st.metric("K Rigidezza", f"{k:.1f}")
                    st.pyplot(plot_shim_bending(k, st.session_state["stack"], d_c, d_p, geo))
                    st.line_chart(df.set_index("Velocità (m/s)")["Forza (N)"])

    with t3:
        with st.form("d"):
            feed = st.text_area("Feedback")
            if st.form_submit_button("Salva") and feed:
                SuspensionDB.save_session(mezzo_sel.split("(")[-1][:-1], "Test", "Secco", feed, 3, {})
                st.success("Salvato")

    with t4:
        st.dataframe(SuspensionDB.get_history_by_mezzo(mezzo_sel.split("(")[-1][:-1]))
