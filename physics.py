import numpy as np
import pandas as pd

class SuspensionPhysics:
    """
    Motore V2: Include calcolo profilo di flessione (Bending Shape).
    """

    @staticmethod
    def calculate_stiffness_factor(stack_list, clamp_d, piston_d):
        if not stack_list: return 0.0
        
        # Parametri base
        E = 206000  # MPa (Acciaio)
        nu = 0.3
        total_stiffness = 0.0
        
        # Ordiniamo lo stack (Pivot è il clamp)
        # Calcolo semplificato del momento d'inerzia equivalente
        for item in stack_list:
            qty = float(item['qty'])
            od = float(item['od'])
            th = float(item['th'])
            
            a = od / 2.0
            b = clamp_d / 2.0
            
            if a <= b: continue
            
            # Roark's Formula per piastra anulare incastrata internamente
            ratio = a / b
            K_geo = (0.18 * (ratio - 1)**2 + 0.5) * (ratio/1.5) # Correzione progressiva
            
            D = (E * (th**3)) / (12 * (1 - nu**2))
            k_single = (D / (a**2 * K_geo))
            
            total_stiffness += k_single * qty

        return total_stiffness * 1000 # Scaling per unità gestibili

    @staticmethod
    def simulate_damping_curve(k_factor, geo_dict):
        """ Restituisce curve forza-velocità e dati sulla flessione massima """
        r_port = geo_dict.get('r_port', 12.0)
        w_port = geo_dict.get('w_port', 8.0)
        n_ports = geo_dict.get('n_ports', 4)
        d_piston = geo_dict.get('d_piston', 50.0)
        d_rod = geo_dict.get('d_rod', 16.0)

        area_piston = np.pi * (d_piston/2)**2 - np.pi * (d_rod/2)**2
        area_port_max = w_port * r_port * 0.5 * n_ports 
        
        velocities = np.linspace(0, 8, 50) # Fino a 8 m/s per vedere high speed
        forces = []
        deflections = [] # Max lift in mm
        
        rho = 870
        Cd = 0.7
        
        # Bleed fisso (clicker)
        A_bleed = 1.5 # mm2

        for v in velocities:
            if v == 0:
                forces.append(0)
                deflections.append(0)
                continue
            
            Q = (area_piston * 1e-6) * v 
            
            # Stima forza idraulica necessaria per aprire lo stack
            # F_opening ~ v * factor / k_factor
            # Più iterazioni renderebbero il calcolo più preciso, qui usiamo approssimazione diretta
            
            # Apertura stimata (y_max alla porta)
            # Logica: La pressione spinge, lo stack resiste.
            # DeltaP stimato iniziale
            
            opening_resistance = k_factor * 15 # Tuning factor
            
            # Modello saturazione: lo stack non apre all'infinito
            y_lift = (v * 400) / (opening_resistance + v*10) 
            if y_lift > 2.0: y_lift = 2.0 # Limite fisico meccanico
            
            # Calcolo Area risultante
            A_curtain = (2 * np.pi * r_port) * y_lift * 0.6 # Area laterale cilindro equivalente
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

        df = pd.DataFrame({
            "Velocità (m/s)": velocities,
            "Forza (N)": forces,
            "Lift (mm)": deflections
        })
        return df

    @staticmethod
    def get_shim_profile(k_factor, d_clamp, max_od, y_max):
        """
        Calcola la forma della curva (X, Y) della lamella piegata.
        Simula una trave incastrata a X=r_clamp con deflessione y_max a X=r_port.
        """
        r_clamp = d_clamp / 2.0
        r_outer = max_od / 2.0
        
        # Generiamo punti lungo il raggio
        radii = np.linspace(r_clamp, r_outer, 50)
        
        # Formula di deflessione trave incastrata: y(x) = Y_max * (x^2 * (3L - x)) / ...
        # Semplificazione parabolica visuale: y = a * (x - x0)^2
        # y(r) = y_max * ((r - r_clamp) / (r_outer - r_clamp))^2
        
        L = r_outer - r_clamp
        if L <= 0: L = 1 # Evita div/0
        
        ys = []
        for r in radii:
            x_local = r - r_clamp
            # Profilo cubic spline semplificato (più realistico della parabola)
            # Shape factor normalized 0 to 1
            norm_x = x_local / L
            # Curva di flessione standard: 2*x^2 - x^3 (approssimazione)
            shape = (norm_x**2) 
            ys.append(y_max * shape)
            
        return radii, ys
