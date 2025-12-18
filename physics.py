import numpy as np
import pandas as pd

class SuspensionPhysics:
    """
    Motore di calcolo per sospensioni.
    Replica la logica base di simulatori tipo Restackor:
    1. Calcola la rigidezza meccanica dello stack (Roark's Formulas per piastre).
    2. Calcola la forza idraulica basata sulla geometria dei port (Bernoulli).
    """

    @staticmethod
    def calculate_stiffness_factor(stack_list, clamp_d, piston_d):
        """
        Calcola un fattore di rigidezza (K) dello stack.
        Input:
            - stack_list: lista di dict {'od': mm, 'th': mm, 'qty': int}
            - clamp_d: diametro del clamp (mm)
            - piston_d: diametro del pistone (mm) (usato per scalare il braccio di leva)
        Output:
            - float: Indice di rigidezza (N/mm eq)
        """
        if not stack_list:
            return 0.0

        # Parametri fisici acciaio armonico
        E = 206000  # Modulo di Young (MPa)
        nu = 0.3    # Coefficiente di Poisson

        total_stiffness = 0.0
        
        # Ordiniamo lo stack dal più grande (vicino al pistone) al più piccolo (clamp)
        # In un calcolo semplificato, sommiamo i contributi di rigidezza.
        
        for item in stack_list:
            qty = float(item['qty'])
            od = float(item['od'])
            th = float(item['th'])
            
            # Raggi
            a = od / 2.0      # Raggio esterno lamella
            b = clamp_d / 2.0 # Raggio interno (vincolo)
            
            if a <= b:
                continue # La lamella è più piccola o uguale al clamp, non lavora
            
            # --- FORMULA DI ROARK (Caso: Piastra circolare forata, bordo est. libero, int. incastrato) ---
            # Semplificazione del coefficiente geometrico K_roark basato sul rapporto a/b
            ratio = a / b
            # Questa è un'approssimazione polinomiale del fattore K per la deflessione
            K_geo = 0.18 * (ratio - 1)**2 + 0.5 
            
            # Rigidezza D della singola lamella (Plate Constant)
            # D = (E * t^3) / (12 * (1 - v^2))
            D = (E * (th**3)) / (12 * (1 - nu**2))
            
            # Rigidezza alla punta (N/mm) -> F / y
            # y = (F * a^2) / D * factor... invertiamo:
            k_single = (D / (a**2 * K_geo)) 
            
            # MOLTIPLICATORE DI LEVA IDRAULICA
            # La pressione non agisce sulla punta, ma su r.port.
            # Più la lamella è grande rispetto al clamp, più è "morbida" all'apparenza.
            # Più spessa è, più è rigida (al cubo).
            
            total_stiffness += k_single * qty

        # Restituisce un numero scalato per essere leggibile (es. 20-500)
        return total_stiffness * 1000 

    @staticmethod
    def simulate_damping_curve(stiffness_factor, geo_dict):
        """
        Genera la curva Forza-Velocità.
        Input:
            - stiffness_factor: Il risultato di calculate_stiffness_factor
            - geo_dict: {'r_port': mm, 'w_port': mm, 'n_ports': int, 'd_piston': mm}
        """
        # Estrai geometria
        r_port = geo_dict.get('r_port', 12.0) # Braccio di leva della pressione
        w_port = geo_dict.get('w_port', 8.0)  # Larghezza passaggio
        n_ports = geo_dict.get('n_ports', 4)
        d_piston = geo_dict.get('d_piston', 50.0)
        d_rod = geo_dict.get('d_rod', 16.0) # Se non c'è, usiamo standard 16

        # Calcolo Aree
        area_piston = np.pi * (d_piston/2)**2 - np.pi * (d_rod/2)**2 # Area idraulica (mm2)
        area_port_max = w_port * r_port * 0.5 * n_ports # Stima area massima passaggi (mm2)
        
        velocities = np.linspace(0, 6, 60) # Da 0 a 6 m/s
        forces = []
        
        # Densità olio (kg/m3) circa 870
        rho = 870 
        
        for v in velocities:
            if v == 0:
                forces.append(0)
                continue
            
            # 1. Portata Olio (Q) in m^3/s
            # Q = Area_pistone * Velocità
            Q = (area_piston * 1e-6) * v 
            
            # 2. Deflessione Stack (Apertura)
            # La pressione apre lo stack. Più è rigido, meno apre.
            # Modello semplificato iterativo:
            # Pressione stimata P ~ v
            # Forza su stack ~ P * Area_port
            # Deflessione y = F_stack / K_stack
            
            # Simuliamo l'apertura progressiva (y)
            # Factor empirico per convertire stiffness in resistenza all'apertura
            opening_resistance = stiffness_factor * 50 
            
            # Area di flusso effettiva (Variable Orifice)
            # A_flow = A_bleed + (A_apertura * v / resistance)
            # Non può superare area_port_max
            
            # Area dinamica che cresce con la velocità (lo stack si piega)
            # Più stiffness è alto, più A_dyn cresce lentamente
            A_dyn = (v * 500) / (opening_resistance + 1)
            
            # Aggiungiamo un bleed fisso (clicker) simulato
            A_bleed = 2.0 # mm2 equivalenti
            
            A_total = A_bleed + A_dyn
            if A_total > area_port_max: A_total = area_port_max
            
            # Converti in m^2
            A_total_m2 = A_total * 1e-6
            
            # 3. Bernoulli: Delta P = 0.5 * rho * (Q / (Cd * A))^2
            Cd = 0.7 # Coefficiente di scarico
            
            try:
                DeltaP = 0.5 * rho * (Q / (Cd * A_total_m2))**2
            except:
                DeltaP = 0
            
            # 4. Forza Totale all'asta
            # F = DeltaP * Area_pistone
            F_newton = DeltaP * (area_piston * 1e-6)
            
            # Converti in kg (opzionale) o lascia in Newton. Qui usiamo Newton.
            forces.append(F_newton)

        # Output DataFrame
        return pd.DataFrame({
            "Velocità (m/s)": velocities,
            "Forza (N)": forces
        })
