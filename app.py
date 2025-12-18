import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import time

# --- IMPORT MODULI ---
try:
    from db_manager import SuspensionDB
    from physics import SuspensionPhysics
except ImportError:
    st.error("⚠️ ERRORE: Assicurati che db_manager.py e physics.py siano presenti.")
    st.stop()

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="SuspensionLab Pro",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PROFESSIONALE ---
st.markdown("""
<style>
    /* Colori Sfondi e Sidebar */
    [data-testid="stSidebar"] { background-color: #1a1c24; border-right: 1px solid #333; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    
    /* Input più leggibili */
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #2b303b !important; color: white !important; border: 1px solid #4a4e59 !important;
    }
    
    /* Header settori */
    .header-fork { color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 5px; margin-bottom: 15px; }
    .header-shock { color: #e67e22; border-bottom: 2px solid #e67e22; padding-bottom: 5px; margin-bottom: 15px; }
    
    /* Tabelle */
    [data-testid="stDataFrame"] { border: 1px solid #444; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONE GRAFICA ---
def plot_shim_bending(k_factor, stack, d_clamp, d_piston, geo_data):
    if not stack: return None
    max_od = max([float(x['od']) for x in stack])
    speeds = [0.5, 2.0, 6.0]
    colors = ['#2ecc71', '#f1c40f', '#e74c3c']
    
    df_sim = SuspensionPhysics.simulate_damping_curve(k_factor, geo_data)
    fig, ax = plt.subplots(figsize=(8, 4))
    
    r_clamp = d_clamp / 2.0
    r_piston = d_piston / 2.0
    r_port = geo_data['r_port']
    
    # Disegno tecnico
    ax.plot([0, r_piston], [0, 0], color='#2c3e50', linewidth=4, label='Pistone') 
    ax.fill_between([0, r_clamp], [0, 0], [0.5, 0.5], color='#34495e', label='Clamp')
    ax.axvline(x=r_port, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    for i, v in enumerate(speeds):
        row = df_sim.iloc[(df_sim['Velocità (m/s)'] - v).abs().argsort()[:1]]
        y_max = row['Lift (mm)'].values[0]
        radii, deflections = SuspensionPhysics.get_shim_profile(k_factor, d_clamp, max_od, y_max)
        ax.plot(radii, deflections, color=colors[i], linewidth=2, label=f'{v} m/s')
        ax.fill_between(radii, deflections, 0, color=colors[i], alpha=0.1)

    ax.set_title("Profilo Flessione Reale", fontsize=10, fontweight='bold')
    ax.set_ylim(-0.5, 3.5)
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, linestyle=':', alpha=0.3)
    return fig

# --- LOGIN ---
if "autenticato" not in st.session_state: st.session_state["autenticato"] = False
if not st.session_state["autenticato"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("🔒 Accesso Riservato")
        if st.text_input("Password", type="password") == "sospensioni2025":
            if st.button("ENTRA", type="primary", use_container_width=True):
                st.session_state["autenticato"] = True
                st.rerun()
    st.stop() 

# --- SIDEBAR (NAVIGATORE) ---
with st.sidebar:
    st.title("🗂️ ARCHIVIO")
    st.markdown("---")
    
    try:
        lista_piloti = SuspensionDB.get_piloti_options()
    except:
        lista_piloti = []

    pilota_sel = st.selectbox("👤 PILOTA", ["Seleziona..."] + lista_piloti)
    
    mezzo_sel_full = None
    id_pilota_corrente = None
    id_mezzo_corrente = None
    
    if pilota_sel != "Seleziona..." and lista_piloti:
        id_pilota_corrente = pilota_sel.split("(")[-1].replace(")", "")
        lista_mezzi = SuspensionDB.get_mezzi_by_pilota(id_pilota_corrente)
        
        mezzo_sel_full = st.selectbox("🏍️ MEZZO", ["Nuovo Mezzo..."] + lista_mezzi)
        
        if mezzo_sel_full and "#" in mezzo_sel_full:
            id_mezzo_corrente = mezzo_sel_full.split("#")[-1]

    st.markdown("---")
    
    with st.expander("➕ Nuovo Pilota"):
        with st.form("new_p", clear_on_submit=True):
            n_nome = st.text_input("Nome Cognome")
            n_tel = st.text_input("Telefono")
            n_peso = st.number_input("Peso", 40, 150, 75)
            n_liv = st.selectbox("Livello", ["Amatore", "Agonista", "Pro"])
            n_note = st.text_area("Note")
            if st.form_submit_button("Salva"):
                if n_nome:
                    SuspensionDB.add_pilota(n_nome, n_peso, n_liv, n_tel, n_note)
                    st.success("Ok")
                    time.sleep(1)
                    st.rerun()

    if id_pilota_corrente:
        with st.expander("➕ Aggiungi Moto"):
            with st.form("new_m", clear_on_submit=True):
                st.write(f"Per: **{pilota_sel.split('(')[0]}**")
                m_tipo = st.selectbox("Tipo", ["MOTO", "MTB"])
                m_marca = st.text_input("Marca")
                m_mod = st.text_input("Modello")
                m_anno = st.number_input("Anno", 2000, 2030, 2024)
                m_fork = st.text_input("Modello Forcella")
                m_mono = st.text_input("Modello Mono")
                
                if st.form_submit_button("Salva Moto"):
                    if m_mod:
                        SuspensionDB.add_mezzo(id_pilota_corrente, m_tipo, m_marca, m_mod, m_anno, m_fork, m_mono)
                        st.success("Moto aggiunta!")
                        time.sleep(1)
                        st.rerun()

# --- MAIN PAGE ---
if id_mezzo_corrente:
    nome_mezzo_display = mezzo_sel_full.split("#")[0]
    st.markdown(f"## 🛠️ {nome_mezzo_display} <span style='font-size:0.6em; color:gray'>Workspace</span>", unsafe_allow_html=True)
    st.markdown("---")

    tab_setup, tab_sim, tab_diario, tab_history = st.tabs(["🔧 SETUP ATTUALE", "🧪 ANALISI & STACK", "📝 DIARIO & NOTE", "🗃️ STORICO"])

    # --- TAB 1: SETUP COMPLETO (Forcella & Mono separati) ---
    with tab_setup:
        # Layout a due colonne separate visivamente
        col_fork, col_shock = st.columns(2)
        
        # --- ZONA FORCELLA ---
        with col_fork:
            st.markdown("<h3 class='header-fork'>🔹 FORCELLA / FRONT</h3>", unsafe_allow_html=True)
            with st.container(border=True):
                c_f1, c_f2 = st.columns(2)
                f_molla = c_f1.number_input("Molla (N/mm o Bar)", value=4.6, step=0.1, key="f_k")
                f_olio = c_f2.number_input("Livello Olio / Quantità", value=350, step=10, key="f_oil")
                
                st.markdown("---")
                c_f3, c_f4, c_f5 = st.columns(3)
                f_comp = c_f3.number_input("Comp", 0, 40, 12, key="f_c")
                f_reb = c_f4.number_input("Reb", 0, 40, 12, key="f_r")
                f_pre = c_f5.number_input("Preload (mm)", 0, 50, 5, key="f_pre")
                
                st.markdown("---")
                f_pos = st.text_input("Posizione (Sfilamento)", "2a Tacca / 5mm", key="f_pos")
                f_note = st.text_area("Note Tecniche Forcella", height=80, key="f_note")

        # --- ZONA MONO ---
        with col_shock:
            st.markdown("<h3 class='header-shock'>🔸 MONO / REAR</h3>", unsafe_allow_html=True)
            with st.container(border=True):
                c_s1, c_s2 = st.columns(2)
                s_molla = c_s1.number_input("Molla (N/mm o Lbs)", value=54.0, step=1.0, key="s_k")
                s_sag = c_s2.number_input("Sag Statico (mm)", value=35, step=1, key="s_sag")
                
                st.markdown("---")
                c_s3, c_s4 = st.columns(2)
                s_comph = c_s3.number_input("Comp HIGH", 0, 40, 10, key="s_ch")
                s_compl = c_s4.number_input("Comp LOW", 0, 40, 12, key="s_cl")
                
                c_s5, c_s6 = st.columns(2)
                s_reb = c_s5.number_input("Reb", 0, 40, 12, key="s_r")
                s_pre = c_s6.number_input("Preload (mm)", 0, 50, 8, key="s_pre")

                st.markdown("---")
                s_len = st.text_input("Interasse / Lunghezza", "Standard", key="s_len")
                s_note = st.text_area("Note Tecniche Mono", height=80, key="s_note")

    # --- TAB 2: ANALISI & TABELLA STACK ---
    with tab_sim:
        col_input, col_graph = st.columns([1.5, 2]) # Più spazio alla tabella
        
        # PARTE SINISTRA: TABELLA STACK & GEOMETRIA
        with col_input:
            # 1. Geometria (Raggruppata per non occupare spazio)
            with st.expander("⚙️ Geometria Valvola", expanded=True):
                cg1, cg2, cg3 = st.columns(3)
                sim_dp = cg1.number_input("Ø Pistone", value=50.0, key="s_dp")
                sim_rp = cg2.number_input("R. Port", value=12.0, key="s_rp")
                sim_dc = cg3.number_input("Ø Clamp", value=12.0, key="s_dc")
                
                geo_data = {"d_piston": sim_dp, "d_rod": 16.0, "r_port": sim_rp, "w_port": 8.0, "n_ports": 4}

            # 2. TABELLA STACK (Il cuore della richiesta)
            st.markdown("##### 🥞 Stack Editor")
            st.caption("Modifica la tabella come su Excel. Aggiungi righe col tasto + in basso.")

            if "stack_df" not in st.session_state:
                # Dati iniziali di esempio
                st.session_state["stack_df"] = pd.DataFrame(
                    [{"qty": 1, "od": 20.0, "th": 0.15}, {"qty": 1, "od": 18.0, "th": 0.15}], 
                    columns=["qty", "od", "th"]
                )

            # EDITOR POTENTE
            edited_df = st.data_editor(
                st.session_state["stack_df"],
                num_rows="dynamic", # Permette di aggiungere/togliere righe
                column_config={
                    "qty": st.column_config.NumberColumn("Q.tà", min_value=1, step=1, format="%d", width="small"),
                    "od": st.column_config.NumberColumn("Ø Esterno (mm)", min_value=6.0, max_value=60.0, step=0.5, format="%.1f"),
                    "th": st.column_config.NumberColumn("Spessore (mm)", min_value=0.05, max_value=0.50, step=0.01, format="%.2f")
                },
                use_container_width=True,
                hide_index=True,
                key="stack_editor_main"
            )
            st.session_state["stack_df"] = edited_df

            if st.button("🔥 AGGIORNA CALCOLI", type="primary", use_container_width=True):
                st.rerun()

        # PARTE DESTRA: RISULTATI GRAFICI
        with col_graph:
            st.markdown("##### 📊 Risultati Analisi")
            
            stack_list = edited_df.to_dict('records')
            
            if stack_list and len(stack_list) > 0:
                try:
                    k = SuspensionPhysics.calculate_stiffness_factor(stack_list, sim_dc, sim_dp)
                    df_res = SuspensionPhysics.simulate_damping_curve(k, geo_data)
                    
                    # Grafico Flessione (Bello grande)
                    st.pyplot(plot_shim_bending(k, stack_list, sim_dc, sim_dp, geo_data))
                    
                    # Grafico Curva
                    st.line_chart(df_res.set_index("Velocità (m/s)")["Forza (N)"], height=250)
                    
                    # Dati numerici rapidi
                    m1, m2 = st.columns(2)
                    m1.metric("K Rigidezza", f"{k:.1f}")
                    m2.metric("Forza Max", f"{df_res['Forza (N)'].max():.0f} N")
                except Exception as e:
                    st.error(f"Errore calcolo: {e}")
            else:
                st.info("Inserisci almeno una lamella nella tabella a sinistra.")

    # --- TAB 3: DIARIO (Salvataggio Sessione) ---
    with tab_diario:
        st.subheader("📝 Report Sessione")
        with st.form("diario_form"):
            c1, c2 = st.columns(2)
            f_pista = c1.text_input("📍 Pista / Luogo")
            f_cond = c2.selectbox("🌤️ Condizione", ["Secco", "Fango", "Sabbia", "Misto", "Bagnato"])
            
            st.markdown("---")
            f_feed = st.text_area("💬 Feedback Pilota / Sensazioni", height=100)
            f_rating = st.slider("⭐ Voto Sessione", 1, 5, 3)
            
            # RACCOLTA DATI PER SALVATAGGIO (Setup + Stack + Geo)
            setup_snapshot = {
                "forcella": {
                    "molla": f_molla, "olio": f_olio, "comp": f_comp, "reb": f_reb, 
                    "preload": f_pre, "pos": f_pos, "note": f_note
                },
                "mono": {
                    "molla": s_molla, "sag": s_sag, "comp_h": s_comph, "comp_l": s_compl, 
                    "reb": s_reb, "preload": s_pre, "len": s_len, "note": s_note
                }
            }
            
            stack_snapshot = st.session_state.get("stack_df", pd.DataFrame()).to_dict('records')
            
            full_data = {
                "setup": setup_snapshot,
                "stack": stack_snapshot,
                "geo": geo_data
            }
            
            if st.form_submit_button("💾 SALVA SESSIONE NEL DB", type="primary"):
                if f_pista:
                    SuspensionDB.save_session(id_mezzo_corrente, f_pista, f_cond, f_feed, f_rating, full_data)
                    st.success("Sessione Salvata con successo!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Inserisci almeno il nome della pista.")

    # --- TAB 4: STORICO ---
    with tab_history:
        st.subheader("🗃️ Storico Interventi")
        df_hist = SuspensionDB.get_history_by_mezzo(id_mezzo_corrente)
        
        if not df_hist.empty:
            for _, row in df_hist.iterrows():
                with st.expander(f"📅 {row['data']} - {row['pista_luogo']} (Voto: {row['rating']})"):
                    st.write(f"**Condizione:** {row['condizione']}")
                    st.write(f"**Feedback:** {row['feedback_text']}")
                    
                    try:
                        # Recupera i dati salvati
                        dati = json.loads(row['dati_tecnici_json'])
                        
                        # Mostra Setup usato
                        if "setup" in dati:
                            sf = dati['setup'].get('forcella', {})
                            sm = dati['setup'].get('mono', {})
                            
                            col_h1, col_h2 = st.columns(2)
                            with col_h1:
                                st.caption("🟦 Setup Forcella")
                                st.json(sf, expanded=False)
                            with col_h2:
                                st.caption("🟧 Setup Mono")
                                st.json(sm, expanded=False)

                        # Mostra Stack usato
                        if "stack" in dati:
                            st.caption("🥞 Stack Usato")
                            st.dataframe(pd.DataFrame(dati['stack']), hide_index=True)
                    except:
                        pass
        else:
            st.info("Nessuna sessione registrata per questa moto.")

else:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("👈 Inizia selezionando un Pilota e una Moto dal menu laterale.")
