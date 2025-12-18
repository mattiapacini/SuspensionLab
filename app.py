import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from physics import SuspensionPhysics
from db_manager import SuspensionDB

st.set_page_config(layout="wide", page_title="SuspensionLab PRO", page_icon="🔧")

# ==============================================================================
# 1. INIZIALIZZAZIONE MEMORIA (Blocco Sicurezza)
# ==============================================================================
if "init_done" not in st.session_state:
    # --- DEFAULT FORCELLA (WP 48 AER/XPLOR style) ---
    st.session_state["fork_bv_df"] = pd.DataFrame([{"qty": 6, "od": 24.0, "th": 0.15}, {"qty": 1, "od": 14.0, "th": 0.10}]) # Base
    st.session_state["fork_mv_df"] = pd.DataFrame([{"qty": 3, "od": 20.0, "th": 0.10}]) # Mid
    
    # Dati Manuale Forcella
    st.session_state["man_f"] = {
        'model': 'WP XACT 48',
        'spring_k': 4.4, 'spring_preload': 5.0, 'oil_level': 350.0, # ml o mm
        'comp_click': 12, 'reb_click': 12,
        'd_piston': 24.0, 'd_rod': 12.0, 'd_clamp': 12.0, 'float': 0.4,
        'oil_visc': 15.0
    }

    # --- DEFAULT MONO (WP LINK/PDS style) ---
    st.session_state["shock_comp_df"] = pd.DataFrame([{"qty": 8, "od": 44.0, "th": 0.20}, {"qty": 1, "od": 36.0, "th": 0.15}])
    st.session_state["shock_reb_df"] = pd.DataFrame([{"qty": 5, "od": 40.0, "th": 0.15}])
    
    # Dati Manuale Mono
    st.session_state["man_s"] = {
        'model': 'WP XPLOR PDS',
        'spring_k': 69.0, 'spring_preload': 8.0, 'gas_press': 10.0, # Bar
        'lsc_click': 15, 'hsc_click': 1.5, 'reb_click': 15, # HSC giri, altri click
        'd_piston': 50.0, 'd_rod': 18.0, 'd_clamp': 16.0, 'float': 0.0,
        'oil_visc': 12.0
    }
    
    st.session_state["current_pilot_id"] = None
    st.session_state["current_bike_id"] = None
    st.session_state["init_done"] = True

# ==============================================================================
# 2. FUNZIONI UTILI
# ==============================================================================
def render_stack(key, label):
    st.caption(f"📑 {label}")
    return st.data_editor(
        st.session_state[f"{key}_df"],
        num_rows="dynamic",
        column_config={
            "qty": st.column_config.NumberColumn("#", min_value=1, format="%d", width="small"),
            "od": st.column_config.NumberColumn("Ø Est", format="%.1f", width="small"),
            "th": st.column_config.NumberColumn("Spess", format="%.2f", width="small")
        },
        use_container_width=True,
        key=f"ed_{key}"
    )

def draw_curve(vels, forces, color, name):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=vels, y=forces, line=dict(color=color, width=3), name=name))
    fig.add_trace(go.Scatter(x=vels, y=[-f for f in forces], line=dict(color=color, width=1, dash='dot'), name='Estensione Simm.'))
    fig.update_layout(
        title=f"Curve {name}", 
        xaxis_title="Velocità (m/s)", yaxis_title="Forza (N)", 
        height=300, margin=dict(l=20,r=20,t=30,b=20),
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# ==============================================================================
# 3. SIDEBAR (ARCHIVIO)
# ==============================================================================
with st.sidebar:
    st.header("🗂️ SCHEDARIO")
    
    # Caricamento Pilota/Moto
    df_p = SuspensionDB.get_piloti()
    opt_p = ["SELEZIONA PILOTA"] + df_p.apply(lambda x: f"{x['Nome']} (ID:{x['ID']})", axis=1).tolist()
    sel_p = st.selectbox("Pilota", opt_p)
    
    if sel_p != "SELEZIONA PILOTA":
        pid = df_p.iloc[opt_p.index(sel_p)-1]["ID"]
        st.session_state["current_pilot_id"] = pid
        
        df_m = SuspensionDB.get_garage(pid)
        opt_m = ["SELEZIONA MOTO"]
        if not df_m.empty: opt_m += df_m.apply(lambda x: f"{x['marca']} {x['modello']}", axis=1).tolist()
        sel_m = st.selectbox("Moto", opt_m)
        
        if sel_m != "SELEZIONA MOTO":
            mid = df_m.iloc[opt_m.index(sel_m)-1]["id_mezzo"]
            st.session_state["current_bike_id"] = mid
            
            st.markdown("---")
            # CARICAMENTO SETUP
            df_s = SuspensionDB.get_sessioni(mid)
            if not df_s.empty:
                opts = df_s.apply(lambda x: f"{x['data']} | {x['pista_luogo']}", axis=1).tolist()
                sel_s = st.selectbox("Storico Schede:", opts)
                if st.button("📥 APRI SCHEDA", use_container_width=True):
                    row = df_s.iloc[opts.index(sel_s)]
                    d = SuspensionDB.parse_json(row['dati_tecnici_json'])
                    
                    # Ripristino Totale (Lamelle + Manuale)
                    if 'f_bv' in d: st.session_state["fork_bv_df"] = pd.DataFrame(d['f_bv'])
                    if 'f_mv' in d: st.session_state["fork_mv_df"] = pd.DataFrame(d['f_mv'])
                    if 'man_f' in d: st.session_state["man_f"] = d['man_f']
                    
                    if 's_comp' in d: st.session_state["shock_comp_df"] = pd.DataFrame(d['s_comp'])
                    if 's_reb' in d: st.session_state["shock_reb_df"] = pd.DataFrame(d['s_reb'])
                    if 'man_s' in d: st.session_state["man_s"] = d['man_s']
                    
                    st.success("Scheda caricata!")
                    st.rerun()
            
            # SALVATAGGIO
            st.markdown("---")
            with st.expander("💾 SALVA SCHEDA"):
                pista = st.text_input("Pista / Evento")
                note = st.text_area("Note del Tecnico")
                if st.button("ARCHIVIA"):
                    pack = {
                        "f_bv": st.session_state["fork_bv_df"].to_dict('records'),
                        "f_mv": st.session_state["fork_mv_df"].to_dict('records'),
                        "man_f": st.session_state["man_f"],
                        "s_comp": st.session_state["shock_comp_df"].to_dict('records'),
                        "s_reb": st.session_state["shock_reb_df"].to_dict('records'),
                        "man_s": st.session_state["man_s"]
                    }
                    SuspensionDB.save_session(mid, pista, "Setup", note, 5, pack)
                    st.toast("Salvato correttamente")

# ==============================================================================
# 4. PAGINA PRINCIPALE
# ==============================================================================

if not st.session_state["current_bike_id"]:
    st.info("👈 Inizia selezionando un pilota dall'archivio a sinistra.")
    st.stop()

# Layout a TAB separate
tab_fork, tab_shock = st.tabs(["🔹 SCHEDA FORCELLA", "🔸 SCHEDA MONO"])

# --- TAB FORCELLA ---
with tab_fork:
    # Creiamo 3 colonne: Sinistra (Lamelle), Centro (Dati Manuale), Destra (Grafico)
    col1, col2, col3 = st.columns([1, 1, 1.2])
    
    mf = st.session_state["man_f"] # Alias breve

    with col1:
        st.subheader("🛠️ Taratura Idraulica")
        st.session_state["fork_bv_df"] = render_stack("fork_bv", "COMPRESSIONE (Base Valve)")
        st.divider()
        st.session_state["fork_mv_df"] = render_stack("fork_mv", "RITORNO (Mid Valve)")

    with col2:
        st.subheader("📋 Dati Manuale")
        st.text_input("Modello Forcella", mf['model'], key="f_mod")
        
        st.markdown("**Molla & Livelli**")
        c_a, c_b = st.columns(2)
        mf['spring_k'] = c_a.number_input("K Molla (N/mm)", 3.0, 6.0, float(mf['spring_k']), step=0.1)
        mf['oil_level'] = c_b.number_input("Olio (ml/mm)", 0.0, 600.0, float(mf['oil_level']), step=5.0)
        mf['spring_preload'] = st.number_input("Precarico Molla (mm)", 0.0, 20.0, float(mf['spring_preload']))

        st.markdown("**Clicker**")
        c_c, c_d = st.columns(2)
        mf['comp_click'] = c_c.number_input("Comp (Click)", 0, 30, int(mf['comp_click']))
        mf['reb_click'] = c_d.number_input("Reb (Click)", 0, 30, int(mf['reb_click']))
        
        with st.expander("⚙️ Geometria Interna (Tech)", expanded=False):
            mf['d_piston'] = st.number_input("Ø Pistone (mm)", 20.0, 50.0, float(mf['d_piston']))
            mf['d_rod'] = st.number_input("Ø Asta (mm)", 10.0, 16.0, float(mf['d_rod']))
            mf['d_clamp'] = st.number_input("Ø Clamp (mm)", 6.0, 25.0, float(mf['d_clamp']))
            mf['float'] = st.number_input("Float (mm)", 0.0, 3.0, float(mf['float']))
            mf['oil_visc'] = st.number_input("Viscosità (cSt)", 2.5, 40.0, float(mf['oil_visc']))
        
        st.session_state["man_f"] = mf # Aggiorna stato

    with col3:
        st.subheader("📈 Analisi")
        # Preparazione Geometria per Physics
        geo_f_sim = {
            'd_piston': mf['d_piston'], 'd_rod': mf['d_rod'], 
            'd_clamp': mf['d_clamp'], 'float': mf['float'],
            'n_port': 4, 'w_port': 8.0 # Default fissi per ora
        }
        
        # Calcolo
        vels = np.linspace(0, 4, 40)
        forces = []
        for v in vels:
            f, _ = SuspensionPhysics.solve_damping(v, st.session_state["fork_bv_df"], geo_f_sim, mf['oil_visc'], mf['comp_click'])
            forces.append(f)
            
        st.plotly_chart(draw_curve(vels, forces, '#00CC96', 'Forcella Comp'), use_container_width=True)
        
        # KPI Rapidi
        st.info(f"**Setup Attuale:** Molla {mf['spring_k']} N/mm | Olio {mf['oil_level']}")


# --- TAB MONO ---
with tab_shock:
    col1s, col2s, col3s = st.columns([1, 1, 1.2])
    
    ms = st.session_state["man_s"] # Alias breve

    with col1s:
        st.subheader("🛠️ Taratura Mono")
        st.session_state["shock_comp_df"] = render_stack("shock_comp", "COMPRESSIONE")
        st.divider()
        st.session_state["shock_reb_df"] = render_stack("shock_reb", "RITORNO")

    with col2s:
        st.subheader("📋 Dati Manuale")
        st.text_input("Modello Mono", ms['model'], key="s_mod")

        st.markdown("**Molla & Gas**")
        c_e, c_f = st.columns(2)
        ms['spring_k'] = c_e.number_input("K Molla (N/mm)", 30.0, 120.0, float(ms['spring_k']), step=1.0)
        ms['gas_press'] = c_f.number_input("Gas (Bar)", 0.0, 20.0, float(ms['gas_press']), step=0.5)
        ms['spring_preload'] = st.number_input("Precarico Ghiera (mm)", 0.0, 25.0, float(ms['spring_preload']))

        st.markdown("**Regolazioni**")
        c_g, c_h = st.columns(2)
        ms['lsc_click'] = c_g.number_input("LSC (Click)", 0, 30, int(ms['lsc_click']))
        ms['hsc_click'] = c_h.number_input("HSC (Giri)", 0.0, 4.0, float(ms['hsc_click']), step=0.25)
        ms['reb_click'] = st.number_input("Reb (Click)", 0, 40, int(ms['reb_click']))
        
        with st.expander("⚙️ Geometria Interna (Tech)", expanded=False):
            ms['d_piston'] = st.number_input("Ø Pistone Mono (mm)", 36.0, 60.0, float(ms['d_piston']))
            ms['d_rod'] = st.number_input("Ø Asta Mono (mm)", 14.0, 22.0, float(ms['d_rod']))
            ms['d_clamp'] = st.number_input("Ø Clamp (mm)", 10.0, 30.0, float(ms['d_clamp']))
            ms['oil_visc'] = st.number_input("Viscosità (cSt)", 2.5, 40.0, float(ms['oil_visc']))
        
        st.session_state["man_s"] = ms

    with col3s:
        st.subheader("📈 Analisi")
        geo_s_sim = {
            'd_piston': ms['d_piston'], 'd_rod': ms['d_rod'], 
            'd_clamp': ms['d_clamp'], 'float': 0.0,
            'n_port': 4, 'w_port': 12.0
        }
        
        forces_s = []
        for v in vels:
            # Uso LSC per il clicker del simulatore
            f, _ = SuspensionPhysics.solve_damping(v, st.session_state["shock_comp_df"], geo_s_sim, ms['oil_visc'], ms['lsc_click'])
            # Aggiungo effetto Pressione Gas (Forza statica = P * Area Asta)
            # 1 Bar = 0.1 MPa = 0.1 N/mm^2. Area Asta in mm^2
            area_rod_mm2 = np.pi * (ms['d_rod']/2)**2
            gas_force = (ms['gas_press'] * 0.1) * area_rod_mm2
            forces_s.append(f + gas_force) # Offset grafico
            
        st.plotly_chart(draw_curve(vels, forces_s, '#EF553B', 'Mono Comp (+Gas)'), use_container_width=True)
        
        # Calcolo SAG Rapido
        w_pilota = 80 # Default
        if st.session_state["current_pilot_id"]:
             # Recupero peso rapido (mockup per non fare query lenta)
             w_pilota = 80.0 
        
        peso_tot = 105 + w_pilota
        sag_statico = (peso_tot * 0.65 * 9.81 * 3.0) / ms['spring_k'] - ms['spring_preload']
        st.metric("SAG Rider Stimato", f"{sag_statico:.1f} mm")
