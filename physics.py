import numpy as np
import pandas as pd

class SuspensionPhysics:
    """
    Motore Fisico SuspensionLab.
    Calcola rigidezza stack e curve di smorzamento idraulico.
    """

    @staticmethod
    def calculate_stiffness_factor(stack_list, clamp_d, piston_d):
        if not stack_list: return 0.0
        
        # Parametri base Acciaio Armonico
        E = 206000  # MPa
        nu = 0.3
        total_stiffness = 0.0
        
        for item in stack_list:
            qty = float(item['qty'])
            od = float(item['od'])
            th = float(item['th'])
            
            a = od / 2.0
            b = clamp_d / 2.0
            
            if a <= b: continue
            
            # Roark's Formula per piastra anulare (semplificata per tuning)
            ratio = a / b
            K_geo = (0.18 * (ratio - 1)**2 + 0.5) * (ratio/1.5)
            
            D = (E * (th**3)) / (12 * (1 - nu**2))
            k_single = (D / (a**2 * K_geo))
            
            total_stiffness += k_single * qty

        # Scaling per leggibilità (es. restituisce 45.0 invece di 0.000045)
        return total_stiffness * 1000 

    @staticmethod
    def simulate_damping_curve(k_factor, geo_dict):
        """ Restituisce curve forza-velocità e dati sulla flessione """
        r_port = geo_dict.get('r_port', 12.0)
        w_port = geo_dict.get('w_port', 8.0)
        n_ports = geo_dict.get('n_ports', 4)
        d_piston = geo_dict.get('d_piston', 50.0)
        d_rod = geo_dict.get('d_rod', 16.0)

        area_piston = np.pi * (d_piston/2)**2 - np.pi * (d_rod/2)**2
        area_port_max = w_port * r_port * 0.5 * n_ports 
        
        velocities = np.linspace(0, 8, 50) 
        forces = []
        deflections = [] 
        
        rho = 870 # Densità olio
        Cd = 0.7  # Coeff scarico
        A_bleed = 1.5 # Clicker simulation
        
        # Fattore di resistenza all'apertura basato sulla rigidezza calcolata
        opening_resistance = k_factor * 15 

        for v in velocities:
            if v == 0:
                forces.append(0)
                deflections.append(0)
                continue
            
            # Portata
            Q = (area_piston * 1e-6) * v 
            
            # Calcolo Lift (Apertura)
            # Modello saturazione: lo stack non apre all'infinito
            y_lift = (v * 400) / (opening_resistance + v*10) 
            if y_lift > 2.0: y_lift = 2.0 # Limite meccanico
            
            # Calcolo Area
            A_curtain = (2 * np.pi * r_port) * y_lift * 0.6 
            if A_curtain > area_port_max: A_curtain = area_port_max
            
            A_total = A_bleed + A_curtain
            A_total_m2 = A_total * 1e-6
            
            try:
                DeltaP = 0.5 * rho * (Q / (Cd * A_total_m2))**2
            except:
                DeltaP = 0
            
            F_newton = DeltaP * (area_piston * 1e-6)
            
            forces.append(F_newton)
            deflections.append(y_lift)

        return pd.DataFrame({
            "Velocità (m/s)": velocities,
            "Forza (N)": forces,
            "Lift (mm)": deflections
        })

    @staticmethod
    def get_shim_profile(k_factor, d_clamp, max_od, y_max):
        """ Calcola la forma della curva (Shape) della lamella """
        r_clamp = d_clamp / 2.0
        r_outer = max_od / 2.0
        radii = np.linspace(r_clamp, r_outer, 50)
        L = r_outer - r_clamp
        if L <= 0: L = 1 
        
        ys = []
        for r in radii:
            x_local = r - r_clamp
            norm_x = x_local / L
            shape = (norm_x**2) # Profilo quadratico (Travi)
            ys.append(y_max * shape)
            
        return radii, ys
