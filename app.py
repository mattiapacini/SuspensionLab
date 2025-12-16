import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
from datetime import datetime

# ==============================================================================
# 1. MOTORE FISICO & MATEMATICO
# ==============================================================================
class PhysicsEngine:
    
    @staticmethod
    def calc_spring_rate(d_wire, d_out, n_coils, material="steel"):
        """Calcola K molla (N/mm) - Formula standard"""
        if n_coils <= 0 or d_wire <= 0: return 0.0
        d_mean = d_out - d_wire
        G = 81500 if material == "steel" else 45000 # Modulo a taglio (N/mm2)
        k = (G * (d_wire**4)) / (8 * (d_mean**3) * n_coils)
        return k # N/mm

    @staticmethod
    def calc_gas_progression(p0, v0_res, rod_dia, stroke_max, steps=50):
        """Calcola la curva di pressione gas adiabatica/isotermica"""
        rod_area = np.pi * (rod_dia/2)**2
        x = np.linspace(0, stroke_max, steps)
        # Volume occupato dallo stelo
        v_rod = rod_area * x 
        # Legge gas
        denom = v0_res - v_rod
        denom[denom <= 0] = 0.001
        
        p_curve = (p0 * v0_res) / denom
        return x, p_curve

    @staticmethod
    def calc_shim_stiffness(stack, d_clamp, h_preload):
        """
        Stima la rigidezza del pacco (f.stack) usando teoria delle piastre.
        """
        if not stack or len(stack) == 0: return 0.1
        
        k_total = 0
        for item in stack:
            od = item.get('OD', 0)
            thk = item.get('Thk', 0)
            qty = item.get('Qty', 1)
            
            if od > d_clamp:
                # Formula semplificata Roark per piastre anulari
                arm = (od - d_clamp) / 2
                if arm > 0:
                    k_shim = (thk**3) / (arm**2) * 1000000 # Scaling factor
                    k_total += k_shim * qty
        
        return k_total

    @staticmethod
    def validate_stack(stack_df, d_port, r_port, d_clamp):
        """Validatore errori assemblaggio"""
        if stack_df is None or stack_df.empty: return [], []
        errors, warnings = [], []
        
        try:
            first = stack_df.iloc[0]
            # 1. Face Shim troppo piccola
            min_req = (r_port * 2) + 1.0
            if first['OD'] < min_req:
                errors.append(f"⛔ ERRORE: La prima lamella ({first['OD']}mm) non copre la porta! Serve > {min_req:.1f}mm.")
            
            # 2. Clamp Check
            last = stack_df.iloc[-1]
            if last['OD'] < d_clamp:
                warnings.append(f"⚠️ Clamp Warning: L'ultima lamella ({last['OD']}) è più piccola del pivot ({d_clamp}).")
        except:
            pass
        return errors, warnings

# ==============================================================================
# 2. GESTIONE DATABASE
# ==============================================================================
class SuspensionDB:
    FILE = "suspension_master_v5.json"
    
    @classmethod
    def load(cls):
        if os.path.exists(cls.FILE):
            with open(cls.FILE, 'r') as f: return json.load(f)
        return {}

    @classmethod
    def save(cls, meta, data):
        db = cls.load()
        key = f"{meta['bike']} - {meta['track']} ({datetime.now().strftime('%Y-%m-%d')})"
        db[key] = {"meta": meta, "data": data}
        with open(cls.FILE, 'w') as f: json.dump(db, f, indent=4)
        return key

# ==============================================================================
# 3. UI COMPONENTS
# ==============================================================================
st.set_page_config(page_title="Suspension Lab MASTER", layout="wide", page_icon="⚙️")

def render_stack_editor(key, d_clamp_default):
    """Editor Lamelle con Turbo Input e Taper Builder (CORRETTO)"""
    st.markdown("**🥞 Shim Stack Editor**")
    
    # --- TOOLBAR ---
    mode = st.radio("Metodo Input", ["Tabella", "Incolla Testo", "Generatore Piramide"], horizontal=True, key=f"{key}_mode")
    
    df_out = pd.DataFrame()
    
    if mode == "Tabella":
        default_data = [{"Qty":1, "OD":30.0, "ID":d_clamp_default, "Thk":0.20}]
        val = st.session_state.get(f"{key}_stack", default_data)
        
        # FIX: Assicuriamoci che val sia convertito in DataFrame prima di passarlo
        df_val = pd.DataFrame(val)
        
        # Config colonne
        cfg = {
            "Qty": st.column_config.NumberColumn("Qty", format="%d"),
            "OD": st.column_config.NumberColumn("OD", format="%.2f"),
            "ID": st.column_config.NumberColumn("ID", format="%.2f"),
            "Thk": st.column_config.NumberColumn("Thk", format="%.3f"),
        }
        
        df_out = st.data_editor(
            df_val, 
            num_rows="dynamic", 
            key=f"{key}_editor", 
            use_container_width=True,
            column_config=cfg
        )
    
    elif mode == "Incolla Testo":
        txt = st.text_area("Incolla formato: Qty x OD x Thk (es: 3 x 30 x 0.15)", height=100, key=f"{key}_txt")
        if st.button("📥 Importa", key=f"{key}_btn_imp"):
            rows = []
            for line in txt.split('\n'):
                parts = line.lower().replace('x', ' ').split()
                if len(parts) >= 3:
                    try:
                        rows.append({"Qty":float(parts[0]), "OD":float(parts[1]), "ID":d_clamp_default, "Thk":float(parts[2])})
                    except: pass
            if rows:
                st.session_state[f"{key}_stack"] = rows
                st.success("Importato! Torna a 'Tabella'.")
                st.rerun()
                
    elif mode == "Generatore Piramide":
        c1, c2, c3, c4 = st.columns(4)
        od_start = c1.number_input("OD Start", 30.0, key=f"{key}_ods")
        od_end = c2.number_input("OD End", 18.0, key=f"{key}_ode")
        step = c3.number_input("Step (mm)", 2.0, key=f"{key}_stp")
        thk = c4.number_input("Thk", 0.15, key=f"{key}_thk")
        if st.button("🏗️ Genera", key=f"{key}_btn_bld"):
            rows = []
            curr = od_start
            while curr >= od_end:
                rows.append({"Qty":1, "OD":curr, "ID":d_clamp_default, "Thk":thk})
                curr -= step
            st.session_state[f"{key}_stack"] = rows
            st.success("Generato! Torna a 'Tabella'.")
            st.rerun()

    # Salva sempre lo stato per l'uso globale se siamo in tabella
    if mode == "Tabella" and not df_out.empty:
        st.session_state[f"{key}_stack"] = df_out.to_dict('records')
    
    return st.session_state.get(f"{key}_stack", [])

def render_valve_detailed(label, key, has_hsc=False):
    """Scheda completa Valvola"""
    st.markdown(f"### 🔧 {label}")
    t1, t2, t3 = st.tabs(["📐 Geometria & Clamp", "🥞 Stack & Turbo Input", "🧮 Molla HSC/ICS"])
    
   # 1. GEOMETRIA
    with t1:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("Pistone")
            # AGGIUNTO min_value=0.0 OVUNQUE
            r_port = st.number_input("r.port (Raggio)", value=12.0, min_value=0.0, step=0.1, key=f"{key}_r")
            d_port = st.number_input("d.port (Largh. Porta)", value=14.0, min_value=0.0, step=0.1, key=f"{key}_d")
            w_port = st.number_input("w.port (Lung. Arco)", value=10.0, min_value=0.0, step=0.1, key=f"{key}_wp", help="Lunghezza dell'arco della porta")
        with c2:
            st.caption("Profilo & Sede")
            w_seat = st.number_input("w.seat (Tenuta)", value=1.5, min_value=0.0, step=0.1, key=f"{key}_ws")
            h_deck = st.number_input("h.deck (Flusso In)", value=0.0, min_value=0.0, step=0.05, key=f"{key}_hd", help="Altezza libera ingresso flusso")
            d_thrt = st.number_input("d.thrt (Gola)", value=9.0, min_value=0.0, step=0.1, key=f"{key}_dt")
        with c3:
            st.caption("Meccanica")
            d_clamp = st.number_input("d.clamp (Pivot)", value=12.0, min_value=0.0, step=0.5, key=f"{key}_dc")
            h_preload = st.number_input("h.preload (Dish)", value=0.0, step=0.05, key=f"{key}_hp", help="Precarico meccanico sulla faccia")
            clicks = st.slider("Clicker", 0, 30, 12, key=f"{key}_clk")

        # Geometry Wizard per d.thrt
        with st.expander("📐 Wizard Geometria (Calcolo Area)"):
            shape = st.selectbox("Forma Porta", ["Circolare", "Fagiolo/Arco"], key=f"{key}_shp")
            if shape == "Fagiolo/Arco":
                area_calc = w_port * d_port # Approx
                equiv_d = np.sqrt(area_calc/np.pi)*2
                st.info(f"Area ≈ {area_calc:.1f} mm² -> d.thrt equiv ≈ {equiv_d:.1f} mm")

    # 2. STACK
    with t2:
        stack_data = render_stack_editor(key, d_clamp)
        # Validatore Live
        errs, warns = PhysicsEngine.validate_stack(pd.DataFrame(stack_data), d_port, r_port, d_clamp)
        for e in errs: st.error(e)
        for w in warns: st.warning(w)

    # 3. MOLLA (Opzionale)
    rate_val = 0.0
    with t3:
        if has_hsc:
            st.markdown("**Calcolatore Molla HSC**")
            mc1, mc2, mc3 = st.columns(3)
            dw = mc1.number_input("Filo (mm)", 3.0, key=f"{key}_sw")
            dout = mc2.number_input("Esterno (mm)", 18.0, key=f"{key}_sod")
            nc = mc3.number_input("Spire", 6.0, key=f"{key}_sn")
            
            calc_k = PhysicsEngine.calc_spring_rate(dw, dout, nc)
            st.metric("Rate Calcolato", f"{calc_k:.1f} N/mm")
            
            use_spring = st.checkbox("Usa questa molla nel calcolo", value=True, key=f"{key}_use_s")
            if use_spring: rate_val = calc_k
        else:
            st.info("Questa valvola non usa molle HSC solitamente.")

    return {
        "stack": stack_data, "geo": {
            "r_port":r_port, "d_port":d_port, "w_port":w_port, 
            "w_seat":w_seat, "h_deck":h_deck, "d_thrt":d_thrt, 
            "d_clamp":d_clamp, "h_preload":h_preload, "clicks":clicks
        },
        "spring_rate": rate_val
    }

# ==============================================================================
# 4. MAIN PAGE
# ==============================================================================
st.title("🛠️ Suspension Lab MASTER V5")

# --- HEADER GLOBALE ---
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    comp_type = c1.selectbox("Componente", ["MONO (Shock)", "FORCELLA (Fork)"])
    d_rod = c2.number_input("Ø Stelo (Rod)", 16.0)
    d_piston = c3.number_input("Ø Pistone (Main)", 50.0)
    p_gas_static = c4.number_input("Pressione Gas (Bar)", 10.0)

# --- CONFIGURAZIONE GAS AVANZATA (Solo Mono) ---
gas_curve = None
if comp_type == "MONO (Shock)":
    with st.expander("🎈 Configurazione Bladder / Reservoir (Avanzata)"):
        gc1, gc2, gc3 = st.columns(3)
        res_diam = gc1.number_input("Ø Serbatoio", 40.0)
        res_len = gc2.number_input("Altezza Gas (mm)", 80.0)
        stroke = gc3.number_input("Corsa Mono (mm)", 60.0)
        
        if st.checkbox("Attiva simulazione compressione gas"):
            v0 = np.pi * (res_diam/2)**2 * res_len
            x_axis, p_curve = PhysicsEngine.calc_gas_progression(p_gas_static, v0, d_rod, stroke)
            gas_curve = (x_axis, p_curve)
            st.caption(f"Pressione fine corsa: {p_curve[-1]:.1f} Bar")

# --- TAB SETUP VALVOLE ---
inputs = {}
st.markdown("---")

if comp_type == "MONO (Shock)":
    tab1, tab2, tab3 = st.tabs(["🎛️ BVC (Adjuster+HSC)", "🔵 MVC (Comp)", "🔴 MVR (Reb)"])
    with tab1: inputs['bvc'] = render_valve_detailed("Adjuster / BVC", "bvc", has_hsc=True)
    with tab2: inputs['mvc'] = render_valve_detailed("Main Piston Comp", "mvc", has_hsc=False)
    with tab3: inputs['mvr'] = render_valve_detailed("Main Piston Reb", "mvr", has_hsc=False)
else:
    tab1, tab2, tab3 = st.tabs(["🟦 BVC (Base)", "🔵 MVC (Mid Comp)", "🔴 MVR (Mid Reb)"])
    with tab1: inputs['bvc'] = render_valve_detailed("Base Valve", "bvc", has_hsc=False)
    with tab2: inputs['mvc'] = render_valve_detailed("Mid Valve Comp", "mvc", has_hsc=False)
    with tab3: inputs['mvr'] = render_valve_detailed("Mid Valve Reb", "mvr", has_hsc=False)

# ==============================================================================
# 5. SIMULAZIONE & DASHBOARD
# ==============================================================================
st.markdown("---")
if st.button("🚀 LANCIA SIMULAZIONE", type="primary", use_container_width=True):
    
    # --- SIMULATORE SEMPLIFICATO PER ESEMPIO ---
    v = np.linspace(0, 4.0, 50)
    
    # Calcolo Rigidezze Stack
    k_bvc = PhysicsEngine.calc_shim_stiffness(inputs['bvc']['stack'], inputs['bvc']['geo']['d_clamp'], inputs['bvc']['geo']['h_preload'])
    k_mvc = PhysicsEngine.calc_shim_stiffness(inputs['mvc']['stack'], inputs['mvc']['geo']['d_clamp'], inputs['mvc']['geo']['h_preload'])
    k_mvr = PhysicsEngine.calc_shim_stiffness(inputs['mvr']['stack'], inputs['mvr']['geo']['d_clamp'], inputs['mvr']['geo']['h_preload'])
    
    # Aggiunta Molle
    k_bvc += inputs['bvc']['spring_rate'] * 10 
    
    # Calcolo Forze (Semplificato)
    f_comp = (v * k_bvc) + (v * k_mvc * 0.8) 
    f_reb = -1 * (v * k_mvr) 
    
    # Calcolo Pressioni
    p_gas_ref = np.mean(gas_curve[1]) if gas_curve else p_gas_static
    p_base = p_gas_ref + (f_comp * 0.1) 
    p_mid = p_base - (v * k_mvc * 0.05) 

    # --- DASHBOARD GRAFICI ---
    
    # TAB 1: DYNO PLOT
    t_g1, t_g2, t_g3, t_g4 = st.tabs(["📈 Dyno Plot", "⚠️ Cavitazione", "📐 X-Ray Stack", "🤖 AI Analysis"])
    
    with t_g1:
        fig_dyno = go.Figure()
        fig_dyno.add_trace(go.Scatter(x=v, y=f_comp, name='Compressione', line=dict(color='blue', width=3)))
        fig_dyno.add_trace(go.Scatter(x=v, y=f_reb, name='Ritorno', line=dict(color='red', width=3)))
        fig_dyno.add_hline(y=0, line_color="gray")
        fig_dyno.update_layout(title="Force vs Velocity", xaxis_title="Velocità (m/s)", yaxis_title="Forza (kg)")
        st.plotly_chart(fig_dyno, use_container_width=True)
        
    with t_g2:
        fig_cav = go.Figure()
        fig_cav.add_trace(go.Scatter(x=v, y=p_base, name='Pressione Base (Gas+BVC)', line=dict(color='green')))
        fig_cav.add_trace(go.Scatter(x=v, y=p_mid, name='Pressione Mid (Dietro Pistone)', line=dict(color='blue')))
        fig_cav.add_hline(y=0, line_color='red', line_dash='dash', annotation_text="CAVITAZIONE")
        
        if gas_curve:
             fig_cav.add_trace(go.Scatter(x=v, y=[gas_curve[1][0]]*len(v), name='Gas Inizio', line=dict(dash='dot', color='gray')))
             fig_cav.add_trace(go.Scatter(x=v, y=[gas_curve[1][-1]]*len(v), name='Gas Fine Corsa', line=dict(dash='dot', color='black')))
             
        st.plotly_chart(fig_cav, use_container_width=True)

    with t_g3:
        st.info("Visualizzazione Deformazione Lamelle (Cross Section)")
        sel_v = st.slider("Velocità Simulazione (m/s)", 0.0, 4.0, 1.0)
        
        # Simulazione grafica deformazione
        idx = int((sel_v / 4.0) * 49)
        if idx >= len(f_comp): idx = len(f_comp) - 1
        force_now = f_comp[idx]
        deflection = force_now / 1000.0 
        
        fig_xray = go.Figure()
        
        # Pistone
        fig_xray.add_shape(type="rect", x0=0, y0=-2, x1=20, y1=0, fillcolor="gray", line_color="black")
        # Clamp
        fig_xray.add_shape(type="rect", x0=0, y0=0, x1=inputs['mvc']['geo']['d_clamp']/2, y1=0.5, fillcolor="gold")
        
        # Lamella 
        x_shim = np.linspace(inputs['mvc']['geo']['d_clamp']/2, 15, 20)
        y_shim = (x_shim - inputs['mvc']['geo']['d_clamp']/2)**2 * deflection * 0.5
        
        fig_xray.add_trace(go.Scatter(x=x_shim, y=y_shim, mode='lines', fill='tozeroy', name=f'Deflessione @ {sel_v}m/s'))
        fig_xray.update_layout(yaxis_range=[-1, 2], title=f"Apertura Stimata: {y_shim[-1]:.2f} mm")
        st.plotly_chart(fig_xray, use_container_width=True)

    with t_g4:
        st.subheader("🤖 AI Data Analyst")
        st.caption("Invia i dati numerici della curva all'Intelligenza Artificiale per un parere tecnico.")
        
        data_packet = {
            "max_force_comp": f"{max(f_comp):.1f} kg",
            "min_pressure": f"{min(p_mid):.1f} bar",
            "cavitation_risk": "YES" if min(p_mid) < 0 else "NO",
            "balance": f"Comp/Reb Ratio at 1m/s: {abs(f_comp[12]/f_reb[12]):.2f}"
        }
        st.json(data_packet)
        
        if st.button("🧠 Genera Report AI (Simulato)"):
            st.success("Analisi completata!")
            st.markdown("""
            > **Report Tecnico:**
            > La curva di compressione mostra una buona progressione iniziale, ma il **precarico HSC sembra eccessivo**. 
            > Il rischio di cavitazione è **ASSENTE** grazie alla pressione gas ben dimensionata.
            > **Consiglio:** Prova a ridurre il `h.preload` sulla BVC di 0.1mm.
            """)

# --- SIDEBAR SAVE/LOAD ---
with st.sidebar:
    st.header("🗂️ Progetto")
    bike = st.text_input("Moto / Modello")
    track = st.text_input("Cliente / Pista")
    if st.button("Salva"):
        if bike:
            SuspensionDB.save({"bike":bike, "track":track, "type":comp_type}, inputs)
            st.success("Salvato!")
