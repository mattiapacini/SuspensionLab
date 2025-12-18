import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from physics import SuspensionPhysics

# --- SETUP PAGINA ---
st.set_page_config(layout="wide", page_title="SuspensionLab PRO", page_icon="⚙️")

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1E1E1E; border-radius: 5px; color: white; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #E67E22; color: white; }
    .metric-card { background-color: #262730; padding: 15px; border-radius: 10px; border: 1px solid #444; }
    .warning-cav { background-color: #ff4b4b; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONI UTILI ---
def render_stack_editor(key_prefix):
    if f"{key_prefix}_df" not in st.session_state:
        st.session_state[f"{key_prefix}_df"] = pd.DataFrame([
            {"qty": 1, "od": 20.0, "th": 0.15},
            {"qty": 1, "od": 18.0, "th": 0.15},
            {"qty": 1, "od": 16.0, "th": 0.15},
            {"qty": 1, "od": 14.0, "th": 0.15},
            {"qty": 1, "od": 12.0, "th": 0.20} # Clamp
        ])
    
    return st.data_editor(
        st.session_state[f"{key_prefix}_df"],
        num_rows="dynamic",
        column_config={
            "qty": st.column_config.NumberColumn("Q.tà", min_value=1, max_value=10, step=1, format="%d"),
            "od": st.column_config.NumberColumn("Ø Est (mm)", min_value=6.0, max_value=60.0, step=0.5, format="%.1f"),
            "th": st.column_config.NumberColumn("Spessore", min_value=0.05, max_value=1.0, step=0.01, format="%.2f")
        },
        use_container_width=True,
        key=f"editor_{key_prefix}"
    )

def calc_stack_stiffness_simple(df):
    # Approssimazione cubica veloce per la reattività dell'UI
    k = 0.0
    try:
        for _, row in df.iterrows():
            t = row['th']
            qty = row['qty']
            k += (t**3) * qty * 1000 # Fattore scala
    except: pass
    return max(k, 0.1)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🗜️ SuspensionLab")
    st.caption("Physics Engine v2.0 (Air/Cavitation)")
    
    st.markdown("### 🏍️ Progetto")
    modello = st.text_input("Modello Moto", "KTM 450 SX-F")
    peso_pilota = st.number_input("Peso Pilota (kg)", 50, 120, 80)

# --- TABS PRINCIPALI ---
tab_fork, tab_shock, tab_chassis = st.tabs(["🔹 FORCELLA (Front)", "🔸 MONO (Rear)", "⚖️ TELAIO & ANALISI"])

# ==============================================================================
# 1. TAB FORCELLA
# ==============================================================================
with tab_fork:
    col_geom, col_air, col_hyd = st.columns([1, 1, 1.5])
    
    with col_geom:
        st.subheader("📏 Geometria")
        f_type = st.selectbox("Sistema Elastico", ["AIR (Pneumatica)", "COIL (Molla)"], index=0)
        f_layout = st.selectbox("Architettura", ["Simmetrica (2 cartucce)", "Split (Aria sx / Olio dx)", "Split Function (Comp sx / Reb dx)"])
        
        st.markdown("---")
        st.caption("Misure Fisiche")
        f_travel = st.number_input("Corsa Totale (mm)", 100, 350, 300)
        f_stelo = st.selectbox("Ø Stelo", [32, 34, 35, 36, 48, 49, 50], index=4)
        f_rod = st.number_input("Ø Asta Cartuccia", 8.0, 14.0, 12.0)
    
    with col_air:
        st.subheader("💨 Molla / Aria")
        if f_type == "AIR":
            st.info("💡 Air Calculator Attivo")
            f_psi = st.number_input("Pressione (PSI)", 40, 200, 145)
            
            with st.expander("🛠️ Volume Tuning (Token)", expanded=True):
                token_type = st.selectbox("Tipo Token", list(SuspensionPhysics.TOKEN_DB.keys()))
                n_tokens = st.slider("Numero Token", 0, 6, 0)
                
                # Calcolo Preview al volo
                vol_token = SuspensionPhysics.TOKEN_DB[token_type] * n_tokens
                st.caption(f"Riduzione Volume: -{vol_token:.1f} cc")
        else:
            st.info("⚙️ Molla Elicoidale")
            f_rate = st.number_input("Rate Molla (N/mm)", 2.0, 15.0, 4.6, step=0.1)
            f_preload_mech = st.number_input("Precarico (mm)", 0, 20, 5)

    with col_hyd:
        st.subheader("💧 Valvole (Damping)")
        
        tab_bv, tab_mv = st.tabs(["Base Valve (Comp)", "Mid Valve (Reb/Comp)"])
        
        with tab_bv:
            st.markdown("**Stack Compressione**")
            df_bv = render_stack_editor("fork_bv")
            
            c1, c2 = st.columns(2)
            f_hdeck = c1.number_input("h.deck (mm)", 0.0, 10.0, 2.0, help="Altezza canale ingresso porta")
            f_dthroat = c2.number_input("Ø Throat (mm)", 0.0, 50.0, 20.0, help="Diametro minimo interno")
        
        with tab_mv:
            st.markdown("**Stack Ritorno/Mid**")
            df_mv = render_stack_editor("fork_mv")
            mid_float = st.number_input("Float (mm)", 0.0, 2.0, 0.3, step=0.05)
    
    # --- GRAFICO FORCELLA ---
    st.markdown("### 📊 Analisi Forcella")
    
    # Calcolo Curve
    travels = np.linspace(0, f_travel, 100)
    
    fig_fork = go.Figure()
    
    if f_type == "AIR":
        geo_air = {'d_stelo': f_stelo, 'travel': f_travel}
        # Curva Standard (0 Token)
        f_air_std = SuspensionPhysics.calc_air_spring(travels, geo_air, f_psi, token_type, 0)
        # Curva Tuned
        f_air_tuned = SuspensionPhysics.calc_air_spring(travels, geo_air, f_psi, token_type, n_tokens)
        
        fig_fork.add_trace(go.Scatter(x=travels, y=f_air_std, mode='lines', line=dict(dash='dash', color='gray'), name=f"{f_psi} PSI (0 Token)"))
        fig_fork.add_trace(go.Scatter(x=travels, y=f_air_tuned, mode='lines', line=dict(color='#3498db', width=3), name=f"{f_psi} PSI ({n_tokens} Token)"))
    else:
        # Curva Molla Lineare
        f_spring = (f_rate * travels) + (f_rate * f_preload_mech)
        fig_fork.add_trace(go.Scatter(x=travels, y=f_spring, mode='lines', line=dict(color='#e67e22', width=3), name=f"Coil {f_rate} N/mm"))

    fig_fork.update_layout(title="Curva Elastica (Forza vs Corsa)", xaxis_title="Corsa (mm)", yaxis_title="Forza (N)", template="plotly_dark", height=400)
    st.plotly_chart(fig_fork, use_container_width=True)


# ==============================================================================
# 2. TAB MONO
# ==============================================================================
with tab_shock:
    c_s1, c_s2, c_s3 = st.columns([1, 1, 1.5])
    
    with c_s1:
        st.subheader("📐 Geometria Shock")
        s_piston = st.number_input("Ø Pistone", 36, 50, 50)
        s_rod = st.number_input("Ø Asta", 14, 18, 16)
        
        st.markdown("---")
        st.caption("Pressurizzazione")
        res_type = st.selectbox("Tipo Serbatoio", ["Bladder", "Pistone Flottante"])
        s_pres = st.number_input("Pressione Azoto (Bar)", 5.0, 20.0, 10.0)
    
    with c_s2:
        st.subheader("🎛️ Registro & Bleed")
        bleed_type = st.selectbox("Tipo Registro", ["Spillo (Standard)", "Poppet (Bitubo/TTX)"])
        
        max_clicks = st.number_input("Click Totali", 10, 40, 24)
        click_val = st.slider("Posizione Clicker (da Chiuso)", 0, max_clicks, 12)
        
        fixed_bleed = st.number_input("Foro Fisso Pistone (mm)", 0.0, 3.0, 0.0, step=0.1, help="Foro trapanato sul pistone")

    with c_s3:
        st.subheader("🥞 Stack Mono")
        st.markdown("**Compressione**")
        df_shock_c = render_stack_editor("shock_comp")
        
        st.markdown("**Ritorno**")
        df_shock_r = render_stack_editor("shock_reb")

    # --- SIMULAZIONE IDRAULICA MONO ---
    st.markdown("---")
    st.subheader("🧪 Simulazione Idraulica & Cavitazione")
    
    col_plot, col_vis = st.columns([2, 1])
    
    with col_plot:
        # Preparazione Dati Simulazione
        k_stack_c = calc_stack_stiffness_simple(df_shock_c)
        geo_shock = {
            'd_piston': s_piston, 'd_rod': s_rod, 'type': 'compression',
            'n_port': 4, 'w_port': 12, 'h_deck': 3.0, 'd_throat': 100 # Standard
        }
        
        # Calcolo Area Bleed
        # Semplificazione lineare: Area max 3mm2 -> 0 a chiusura
        max_bleed_area = 3.0
        clicker_area = max_bleed_area * (click_val / max_clicks)
        fixed_area = np.pi * (fixed_bleed/2)**2
        
        # Sweep Velocità
        vels = np.linspace(0.01, 6.0, 50)
        forces_c = []
        lifts_c = []
        
        cav_limit = SuspensionPhysics.calc_cavitation_limit(s_pres, s_rod, s_piston)
        
        for v in vels:
            f, l = SuspensionPhysics.solve_damping(v, k_stack_c, geo_shock, clicker_area, fixed_area)
            forces_c.append(f)
            lifts_c.append(l)
            
        # Plot
        fig_damp = go.Figure()
        
        # Area Range (Min-Max Clicker)
        # Calcoliamo veloce i limiti
        f_hard = [SuspensionPhysics.solve_damping(v, k_stack_c, geo_shock, 0, fixed_area)[0] for v in vels]
        f_soft = [SuspensionPhysics.solve_damping(v, k_stack_c, geo_shock, max_bleed_area, fixed_area)[0] for v in vels]
        
        fig_damp.add_trace(go.Scatter(
            x=np.concatenate([vels, vels[::-1]]),
            y=np.concatenate([f_hard, f_soft[::-1]]),
            fill='toself', fillcolor='rgba(52, 152, 219, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            name='Range Clicker'
        ))
        
        # Curva Attuale
        fig_damp.add_trace(go.Scatter(x=vels, y=forces_c, mode='lines', name='Setup Attuale', line=dict(color='#E74C3C', width=3)))
        
        # Linea Cavitazione
        fig_damp.add_hline(y=cav_limit, line_dash="dash", line_color="red", annotation_text="LIMITE CAVITAZIONE", annotation_position="top right")

        # Zone Helper
        fig_damp.add_vrect(x0=0, x1=0.2, fillcolor="green", opacity=0.1, annotation_text="Grip", annotation_position="top left")
        fig_damp.add_vrect(x0=1.5, x1=6.0, fillcolor="orange", opacity=0.1, annotation_text="Impact", annotation_position="top left")

        fig_damp.update_layout(
            title="Damping Force (Compressione)",
            xaxis_title="Velocità Asta (m/s)",
            yaxis_title="Forza (N)",
            template="plotly_dark",
            height=450
        )
        st.plotly_chart(fig_damp, use_container_width=True)
        
        # Check Cavitazione
        max_force = max(forces_c)
        if max_force > cav_limit:
            st.markdown(f"<div class='warning-cav'>⚠️ ALLARME CAVITAZIONE! <br>Forza Picco ({max_force:.0f}N) > Limite ({cav_limit:.0f}N). <br>Aumenta Pressione Gas o Riduci Stack.</div>", unsafe_allow_html=True)

    with col_vis:
        st.markdown("#### 👁️ Visualizer")
        st.caption("Muovi lo slider per vedere l'apertura")
        
        v_sim = st.slider("Velocità (m/s)", 0.0, 6.0, 1.0, 0.1)
        
        # Trova il lift a questa velocità
        idx = (np.abs(vels - v_sim)).argmin()
        current_lift = lifts_c[idx]
        
        st.metric("Apertura Lamelle", f"{current_lift:.2f} mm")
        
        # Disegno Lamella Semplificato
        fig_shim = go.Figure()
        
        r_clamp = 6.0
        r_piston = s_piston / 2
        
        # Lamella a riposo
        fig_shim.add_trace(go.Scatter(x=[r_clamp, r_piston], y=[0, 0], mode='lines', line=dict(color='gray', width=2), name='Riposo'))
        
        # Lamella deformata (Parabolica approx)
        x_shim = np.linspace(r_clamp, r_piston, 20)
        # y = lift * ((x - clamp)/(piston-clamp))^2
        y_shim = current_lift * ((x_shim - r_clamp) / (r_piston - r_clamp))**2
        
        fig_shim.add_trace(go.Scatter(x=x_shim, y=y_shim, mode='lines', line=dict(color='#E74C3C', width=4), name='Deformazione'))
        
        # Pistone
        fig_shim.add_trace(go.Scatter(x=[r_piston, r_piston+5], y=[0, 0], mode='lines', line=dict(color='white', width=5), name='Pistone'))
        
        fig_shim.update_layout(
            title=f"Sezione @ {v_sim} m/s",
            yaxis_range=[-0.5, 3.0],
            xaxis_title="Raggio (mm)",
            yaxis_title="Lift (mm)",
            template="plotly_dark",
            height=300,
            showlegend=False
        )
        st.plotly_chart(fig_shim, use_container_width=True)

# ==============================================================================
# 3. TAB TELAIO (CHASSIS)
# ==============================================================================
with tab_chassis:
    st.subheader("⚖️ Analisi Bilanciamento")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.info("Funzione Target Weight")
        target_w = st.number_input("Peso Target Pilota (kg)", 50, 120, 90)
        
        ratio = target_w / peso_pilota
        st.write(f"Variazione Peso: **{((ratio-1)*100):.1f}%**")
        st.write(f"Nuova Molla Consigliata: **{(f_rate * ratio):.2f} N/mm**")
        st.write(f"Nuovo Damping Consigliato: **+{(np.sqrt(ratio)-1)*100:.1f}%** (Idraulica)")

    with col_t2:
        st.warning("🚧 Drop Test Simulator")
        st.caption("Simulazione atterraggio da 1.5m")
        st.progress(75, text="Utilizzo Corsa Previsto: 280mm / 300mm (OK)")
