import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
from datetime import datetime

# ==============================================================================
# 1. MOTORE FISICO & IDRAULICO (V6 ENGINEERING)
# ==============================================================================
class PhysicsEngine:
    
    @staticmethod
    def calc_spring_rate(d_wire, d_out, n_coils, material="steel"):
        """Calcola K molla (kg/mm)"""
        if n_coils <= 0 or d_wire <= 0: return 0.0
        d_mean = d_out - d_wire
        G = 81500 if material == "steel" else 45000 # N/mm2
        k_newton = (G * (d_wire**4)) / (8 * (d_mean**3) * n_coils)
        return k_newton / 9.806 # Ritorna kg/mm

    @staticmethod
    def calc_gas_pressure(p0_bar, v0_cc, rod_dia_mm, stroke_mm, steps=50):
        """Calcola la progressione gas nel serbatoio"""
        rod_area = np.pi * (rod_dia_mm/2)**2 
        x = np.linspace(0, stroke_mm, steps)
        # Volume occupato dallo stelo che entra
        vol_rod_x = (rod_area * x) / 1000.0
        curr_vol = v0_cc - vol_rod_x
        curr_vol[curr_vol <= 0.1] = 0.1 
        
        # Politropica 1.2 (compromesso tra adiabatico e isotermico)
        gamma = 1.2
        p_curve = p0_bar * (v0_cc / curr_vol)**gamma
        return x, p_curve

    @staticmethod
    def calc_shim_stiffness_factor(stack, d_clamp):
        """Stima fattore K idraulico basato su spessore^3"""
        if not stack: return 0.05
        k_tot = 0
        for s in stack:
            # Calcolo solo se la lamella è attiva (OD > clamp)
            if s['OD'] > d_clamp:
                leverage = (s['OD'] - d_clamp)
                if leverage > 0:
                    # Formula empirica proporzionale alla cubica dello spessore
                    k_shim = (s['Thk']**3) / (leverage**2) * s['Qty']
                    k_tot += k_shim
        return k_tot * 100000 # Scaling factor per simulazione

    @staticmethod
    def calc_hydraulic_pressures(vel_axis, k_bvc, k_mvc, k_mvr, p_gas_curve, d_rod, d_piston):
        """Calcola le pressioni nelle 3 camere (Compressione, Ritorno, Serbatoio)"""
        # Aree in cm2 per calcolo Bar
        area_rod = (np.pi * (d_rod/2)**2) / 100.0
        area_piston = (np.pi * (d_piston/2)**2) / 100.0
        # area_annulus = area_piston - area_rod 
        
        p_res = np.mean(p_gas_curve) # Pressione media serbatoio
        
        p_comp_chamber = [] # Sotto il pistone
        p_reb_chamber = []  # Sopra il pistone (Rischio cavitazione)
        
        for v in vel_axis:
            # Delta P generato dalle valvole
            # BVC gestisce il flusso dell'asta
            dp_bvc = v * k_bvc * (area_rod / 1.0) 
            # MVC gestisce il flusso del pistone
            dp_mvc = v * k_mvc * (area_piston / 1.0)
            
            # Pressione Sotto = P_Gas + Resistenza BVC
            p_c = p_res + dp_bvc
            # Pressione Sopra = P_Sotto - Resistenza MVC
            p_r = p_c - dp_mvc
            
            p_comp_chamber.append(p_c)
            p_reb_chamber.append(p_r)

        return np.array(p_comp_chamber), np.array(p_reb_chamber), p_res

# ==============================================================================
# 2. DATABASE (SALVATAGGIO) - RIPRISTINATO
# ==============================================================================
class SuspensionDB:
    FILE = "suspension_master_db.json"
    
    @classmethod
    def load(cls):
        if os.path.exists(cls.FILE):
            with open(cls.FILE, 'r') as f: return json.load(f)
        return {}

    @classmethod
    def save(cls, meta, data):
        db = cls.load()
        # Chiave unica basata su Moto + Data
        key = f"{meta['bike']} - {meta['track']} ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        db[key] = {"meta": meta, "data": data}
        with open(cls.FILE, 'w') as f: json.dump(db, f, indent=4)
        return key

# ==============================================================================
# 3. UI COMPONENTS & HELPERS
# ==============================================================================
st.set_page_config(page_title="Suspension Lab MASTER V6", layout="wide", page_icon="⚙️")

def draw_stack_visualizer(stack_data, d_clamp, title):
    """Disegna le lamelle reali impilate (X-Ray)"""
    if not stack_data: return go.Figure()
    
    fig = go.Figure()
    y_cursor = 0.0
    
    # Disegna Clamp (Base)
    fig.add_shape(type="rect", x0=-d_clamp/2, y0=-1.0, x1=d_clamp/2, y1=0, fillcolor="gold", line_color="black")
    
    max_w = 0
    # Disegna Lamelle
    for s in stack_data:
        w = s['OD'] / 2.0
        h = s['Thk'] * s['Qty']
        if w > max_w: max_w = w
        
        fig.add_shape(type="rect", 
            x0=-w, y0=y_cursor, x1=w, y1=y_cursor+h, 
            fillcolor="silver", line_color="black", opacity=0.9
        )
        # Hover invisibile
        fig.add_trace(go.Scatter(x=[0], y=[y_cursor + h/2], mode='markers', marker=dict(opacity=0),
            hoverinfo='text', hovertext=f"OD: {s['OD']} x {s['Thk']} (Qty: {s['Qty']})"))
        y_cursor += h
        
    fig.add_shape(type="rect", x0=-2, y0=0, x1=2, y1=y_cursor+0.5, fillcolor="gray", line_width=0)
    fig.update_layout(title=title, xaxis=dict(visible=False, range=[-max_w*1.5, max_w*1.5]), 
                      yaxis=dict(title="Altezza (mm)"), height=250, margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
    return fig

def render_stack_editor(key, d_clamp_default):
    """Editor Lamelle Intelligente (Auto-ID)"""
    st.markdown("**🥞 Editor Lamelle**")
    mode = st.radio("Metodo", ["Tabella", "Incolla Testo"], horizontal=True, key=f"{key}_mode", label_visibility="collapsed")
    
    if mode == "Tabella":
        # Default data con ID automatico dal clamp
        default_data = [{"Qty":1, "OD":30.0, "ID":d_clamp_default, "Thk":0.20}]
        val = st.session_state.get(f"{key}_stack", default_data)
        
        df_out = st.data_editor(pd.DataFrame(val), num_rows="dynamic", key=f"{key}_ed", use_container_width=True,
                                column_config={
                                    "Qty": st.column_config.NumberColumn(format="%d"),
                                    "OD": st.column_config.NumberColumn(format="%.2f"),
                                    "ID": st.column_config.NumberColumn(format="%.2f"), # ID Modificabile
                                    "Thk": st.column_config.NumberColumn(format="%.3f"),
                                })
        if not df_out.empty: st.session_state[f"{key}_stack"] = df_out.to_dict('records')
        
    else:
        txt = st.text_area("Incolla (Qty x OD x Thk)", height=100, key=f"{key}_txt")
        if st.button("Importa", key=f"{key}_btn"):
            rows = []
            for line in txt.split('\n'):
                p = line.lower().replace('x', ' ').split()
                if len(p) >= 3: 
                    # Auto-fill ID con d_clamp_default
                    rows.append({"Qty":float(p[0]), "OD":float(p[1]), "ID":d_clamp_default, "Thk":float(p[2])})
            if rows: 
                st.session_state[f"{key}_stack"] = rows
                st.rerun()

    return st.session_state.get(f"{key}_stack", [])

def render_valve_detailed(label, key, has_hsc=False):
    """Scheda Valvola Completa (Con Limiti 0.0 e HSC Ibrido)"""
    st.markdown(f"### {label}")
    t1, t2, t3 = st.tabs(["📐 Geometria", "🥞 Stack", "🧮 Molla HSC"])
    
    with t1:
        c1, c2, c3 = st.columns(3)
        # MIN_VALUE=0.0 OVUNQUE PER EVITARE BLOCCHI SU BVC
        r_port = c1.number_input("r.port (Raggio)", 0.0, 100.0, 12.0, step=0.1, key=f"{key}_r")
        d_port = c1.number_input("d.port (Largh)", 0.0, 50.0, 14.0, step=0.1, key=f"{key}_d")
        w_port = c1.number_input("w.port (Arco)", 0.0, 50.0, 10.0, step=0.1, key=f"{key}_wp")
        n_thrt = c1.number_input("N.thrt (Num Porte)", 1, 10, 4, key=f"{key}_nt")
        
        w_seat = c2.number_input("w.seat (Tenuta)", 0.0, 10.0, 1.5, step=0.1, key=f"{key}_ws")
        h_deck = c2.number_input("h.deck", 0.0, 10.0, 0.0, step=0.05, key=f"{key}_hd")
        d_thrt = c2.number_input("d.thrt (Gola)", 0.0, 50.0, 9.0, step=0.1, key=f"{key}_dt")
        
        d_clamp = c3.number_input("d.clamp", 0.0, 50.0, 12.0, step=0.5, key=f"{key}_dc")
        h_preload = c3.number_input("h.preload (Dish)", 0.0, 5.0, 0.0, step=0.05, key=f"{key}_hp")
        clicks = c3.slider("Clicks", 0, 30, 12, key=f"{key}_clk")

    with t2:
        # Passiamo d_clamp all'editor per l'auto-fill dell'ID
        stack = render_stack_editor(key, d_clamp)

    rate_kg = 0.0
    hsc_pre = 0.0
    d_hsc = 0.0
    with t3:
        if has_hsc:
            st.caption("Configurazione Molla High Speed / Check")
            c_k1, c_k2 = st.columns(2)
            method = c_k1.radio("Metodo Input K", ["Inserimento kg/mm", "Calcolo Filo"], horizontal=True, key=f"{key}_m")
            
            # Parametri comuni
            cp1, cp2 = st.columns(2)
            hsc_pre = cp1.number_input("Preload (mm)", 0.0, 20.0, 2.0, step=0.1, key=f"{key}_pre")
            d_hsc = cp2.number_input("D.hsc (Appoggio)", 0.0, 50.0, 18.0, step=0.5, key=f"{key}_dhsc")
            
            if method == "Inserimento kg/mm":
                rate_kg = st.number_input("K Molla (kg/mm)", 0.0, 200.0, 5.0, step=0.1, key=f"{key}_kman")
            else:
                dw = st.number_input("Filo (mm)", 0.1, 10.0, 3.0, step=0.1, key=f"{key}_dw")
                dout = st.number_input("Esterno (mm)", 5.0, 50.0, 20.0, step=0.5, key=f"{key}_do")
                nc = st.number_input("Spire Totali", 1.0, 20.0, 6.0, step=0.5, key=f"{key}_nc")
                rate_kg = PhysicsEngine.calc_spring_rate(dw, dout, nc)
                st.success(f"K Calcolato: **{rate_kg:.2f} kg/mm**")
        else:
            st.info("Nessuna molla elicoidale prevista su questa valvola (es. Mid Valve).")

    return {
        "stack": stack, 
        "geo": {"d_clamp":d_clamp, "n_thrt":n_thrt, "r_port":r_port, "h_preload":h_preload},
        "hsc": {"k_kg": rate_kg, "preload": hsc_pre, "d_hsc": d_hsc}
    }

# ==============================================================================
# 4. MAIN APP LAYOUT
# ==============================================================================
st.title("🛠️ Suspension Lab MASTER V6")

# --- SIDEBAR (SALVATAGGIO) ---
with st.sidebar:
    st.header("🗂️ Progetto")
    bike_in = st.text_input("Moto / Modello")
    track_in = st.text_input("Cliente / Setup")
    
    # Placeholder per il salvataggio (verrà attivato alla fine)
    save_btn = st.button("💾 Salva nel Database")

# --- HEADER SETUP ---
with st.expander("⚙️ Parametri Generali Sospensione", expanded=True):
    hc1, hc2, hc3, hc4 = st.columns(4)
    c_type = hc1.selectbox("Componente", ["MONO", "FORK"])
    d_rod = hc2.number_input("Ø Rod (mm)", 10.0, 20.0, 16.0 if c_type=="MONO" else 12.0)
    d_main = hc3.number_input("Ø Main Piston (mm)", 20.0, 60.0, 50.0)
    p_gas_static = hc4.number_input("P. Gas Static (Bar)", 0.0, 30.0, 10.0)
    
    # Gas Avanzato
    st.markdown("---")
    gc1, gc2, gc3 = st.columns(3)
    res_vol = gc1.number_input("Vol. Serbatoio (cc)", 10.0, 500.0, 150.0)
    stroke = gc2.number_input("Corsa Totale (mm)", 50.0, 300.0, 60.0)
    
    # Calcolo Gas Curve Subito (per riferimento)
    gas_x, gas_p = PhysicsEngine.calc_gas_pressure(p_gas_static, res_vol, d_rod, stroke)

# --- INPUT VALVOLE ---
inputs = {}
st.markdown("---")
if c_type == "MONO":
    t_bvc, t_mvc, t_mvr = st.tabs(["🎛️ BVC (Adjuster)", "🔵 MVC (Comp)", "🔴 MVR (Reb)"])
    with t_bvc: inputs['bvc'] = render_valve_detailed("BVC", "bvc", has_hsc=True)
    with t_mvc: inputs['mvc'] = render_valve_detailed("MVC", "mvc", has_hsc=False)
    with t_mvr: inputs['mvr'] = render_valve_detailed("MVR", "mvr", has_hsc=False)
else:
    t_bvc, t_mvc, t_mvr = st.tabs(["Base Valve", "Mid Comp", "Mid Reb"])
    with t_bvc: inputs['bvc'] = render_valve_detailed("Base", "bvc", has_hsc=False)
    with t_mvc: inputs['mvc'] = render_valve_detailed("Mid Comp", "mvc", has_hsc=False)
    with t_mvr: inputs['mvr'] = render_valve_detailed("Mid Reb", "mvr", has_hsc=False)

# --- VISUALIZZAZIONE FISICA STACK (X-RAY) ---
st.markdown("---")
st.subheader("📐 Stack X-Ray (Visualizzazione Fisica)")
xc1, xc2, xc3 = st.columns(3)
with xc1: st.plotly_chart(draw_stack_visualizer(inputs['bvc']['stack'], inputs['bvc']['geo']['d_clamp'], "BVC Stack"), use_container_width=True)
with xc2: st.plotly_chart(draw_stack_visualizer(inputs['mvc']['stack'], inputs['mvc']['geo']['d_clamp'], "MVC Stack"), use_container_width=True)
with xc3: st.plotly_chart(draw_stack_visualizer(inputs['mvr']['stack'], inputs['mvr']['geo']['d_clamp'], "MVR Stack"), use_container_width=True)

# --- LOGICA DI SALVATAGGIO (Eseguita qui per avere 'inputs' pieno) ---
if save_btn:
    if bike_in:
        SuspensionDB.save({"bike":bike_in, "track":track_in, "type":c_type}, inputs)
        st.sidebar.success("✅ Salvato con successo!")
    else:
        st.sidebar.error("❌ Inserisci nome Moto!")

# --- SIMULAZIONE ---
st.markdown("---")
if st.button("🚀 CALCOLA DYNO & CAVITAZIONE", type="primary", use_container_width=True):
    
    # 1. Calcolo Fattori di Rigidezza (K_shim)
    k_bvc = PhysicsEngine.calc_shim_stiffness_factor(inputs['bvc']['stack'], inputs['bvc']['geo']['d_clamp'])
    k_mvc = PhysicsEngine.calc_shim_stiffness_factor(inputs['mvc']['stack'], inputs['mvc']['geo']['d_clamp'])
    k_mvr = PhysicsEngine.calc_shim_stiffness_factor(inputs['mvr']['stack'], inputs['mvr']['geo']['d_clamp'])
    
    # Aggiunta HSC Molla al K della BVC
    if inputs['bvc']['hsc']['k_kg'] > 0:
        # La molla lavora in parallelo. Aggiungiamo un termine lineare 'pesato'
        k_bvc += inputs['bvc']['hsc']['k_kg'] * 50 
    
    # 2. Generazione Assi
    v_sim = np.linspace(0, 4.0, 50) # 0 a 4 m/s
    
    # 3. Calcolo Forze (Kgf)
    # Forza Compressione = (V * K_BVC) + (V * K_MVC)
    f_comp = (v_sim * k_bvc) + (v_sim * k_mvc * 0.8) 
    # Forza Ritorno = V * K_MVR
    f_reb = -1 * (v_sim * k_mvr * 1.2)
    
    # 4. Calcolo Pressioni Camere (Bar)
    p_comp, p_reb, p_res_avg = PhysicsEngine.calc_hydraulic_pressures(
        v_sim, k_bvc, k_mvc, k_mvr, gas_p, d_rod, d_main
    )

    # OUTPUT GRAFICI
    tab_g1, tab_g2 = st.tabs(["📈 Dyno (Force vs Vel)", "⚠️ Cavitazione (Pressure Analysis)"])
    
    with tab_g1:
        fig_d = go.Figure()
        fig_d.add_trace(go.Scatter(x=v_sim, y=f_comp, name='Compression', line=dict(color='blue')))
        fig_d.add_trace(go.Scatter(x=v_sim, y=f_reb, name='Rebound', line=dict(color='red')))
        fig_d.add_hline(y=0, line_color='black', line_width=1)
        fig_d.update_layout(
            title="Curve Forza Smorzamento",
            xaxis_title="Velocità Stelo (m/s)",
            yaxis_title="Forza (kgf)",
            hovermode="x unified"
        )
        st.plotly_chart(fig_d, use_container_width=True)
        
    with tab_g2:
        fig_p = go.Figure()
        
        # 1. Pressione Serbatoio (Riferimento)
        fig_p.add_trace(go.Scatter(x=v_sim, y=[p_res_avg]*len(v_sim), name='Reservoir (Gas)', line=dict(color='green', dash='dot')))
        
        # 2. Pressione Camera Compressione (Sotto il pistone, spinta da BVC)
        fig_p.add_trace(go.Scatter(x=v_sim, y=p_comp, name='Comp Chamber (Bottom)', line=dict(color='orange')))
        
        # 3. Pressione Camera Ritorno (Sopra il pistone - RISCHIO CAVITAZIONE)
        # Questa è la pressione CRITICA. Se scende troppo, cavita.
        fig_p.add_trace(go.Scatter(x=v_sim, y=p_reb, name='Reb Chamber (Top)', line=dict(color='red', width=3)))
        
        # Zona Pericolo
        fig_p.add_hrect(y0=-10, y1=0, fillcolor="red", opacity=0.1, annotation_text="VACUUM / CAVITATION")
        fig_p.add_hline(y=0, line_color="black")
        
        fig_p.update_layout(
            title="Analisi Pressioni Interne (Fase Compressione)",
            xaxis_title="Velocità Stelo (m/s)",
            yaxis_title="Pressione Assoluta (Bar)",
            hovermode="x unified"
        )
        st.caption("Nota: Se la linea rossa scende sotto zero, la sospensione sta cavitando dietro al pistone (Vacuum).")
        st.plotly_chart(fig_p, use_container_width=True)
