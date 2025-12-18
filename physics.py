import numpy as np
import pandas as pd

class SuspensionPhysics:
    
    @staticmethod
    def calculate_stiffness_factor(stack_list, clamp_d, piston_d):
        """
        Calcola un indice di rigidezza basato sulla teoria delle piastre circolari.
        Non è un FEA completo (come Restackor), ma una buona approssimazione analitica.
        """
        if not stack_list:
            return 0, []

        # Convertiamo in DataFrame per comodità
        df = pd.DataFrame(stack_list)
        
        # Parametri fisici
        E = 200000  # Modulo Young Acciaio (MPa)
        nu = 0.3    # Coefficiente Poisson
        
        total_stiffness = 0
        
        # Algoritmo semplificato "Roark's Formula" per piastre anulari
        # Calcoliamo la rigidezza equivalente sommando i contributi
        # Nota: In un simulatore reale servirebbe considerare l'interazione tra lamelle (friction)
        
        for _, shim in df.iterrows():
            # Geometria
            a = shim['od'] / 2.0  # Raggio esterno
            b = clamp_d / 2.0     # Raggio interno (Clamp)
            t = shim['th']        # Spessore
            
            if a <= b: continue # La lamella è più piccola del clamp, non flette
            
            # Fattore geometrico K per piastra incastrata al centro e caricata uniformemente
            # (Approssimazione del carico idraulico distribuito)
            ratio = a / b
            # Formula empirica semplificata per la costante di rigidezza
            K_geo = (0.17 * ratio**2) # Semplificazione coefficiente Roark
            
            # Rigidezza della singola lamella (N/mm)
            # D = E * t^3 / (12 * (1 - nu^2))
            D = (E * t**3) / (12 * (1 - nu**2))
            
            # Deflessione y = q * a^4 / D * K ... invertiamo per trovare la rigidezza
            # Stiffness pro capite pesata sulla quantità
            k_shim = (D / (a**2 * K_geo)) * shim['qty']
            
            total_stiffness += k_shim
            
        return total_stiffness

    @staticmethod
    def simulate_damping_curve(stiffness_nm, geometry_dict):
        """
        Genera la curva Forza/Velocità basata su Bernoulli e l'apertura delle lamelle.
        """
        # Estrai parametri geometrici del pistone
        r_port = geometry_dict.get('r_port', 10.0) # Raggio centro passaggi
        w_port = geometry_dict.get('w_port', 8.0)  # Larghezza passaggi
        n_ports = geometry_dict.get('n_ports', 4)  # Numero passaggi
        
        # Area passaggi a "valvola aperta" (Saturation)
        max_area = (w_port * r_port * 2 * np.pi / n_ports) * n_ports # Semplificato
        
        velocities = np.linspace(0, 5, 50) # Da 0 a 5 m/s
        forces = []
        
        for v in velocities:
            if v == 0:
                forces.append(0)
                continue
            
            # 1. Calcolo Pressione richiesta per spingere quel flusso (Bernoulli base)
            # Q (Portata) = Velocità stelo * Area Pistone
            area_piston = np.pi * (50/2)**2 - np.pi * (12/2)**2 # Es. 50mm pistone, 12mm asta
            Q = v * area_piston / 1000 # Litri/sec ca. (unità da aggiustare)
            
            # 2. La pressione spinge le lamelle -> Forza sulle lamelle
            # Forza Idraulica = Pressione * Area passaggi
            # Ma la Pressione dipende dall'apertura (Area_effettiva)
            # Area_effettiva dipende dalla deflessione (Stiffness)
            
            # Iterazione per trovare l'equilibrio (semplificata)
            # F_shim = K * x (x = apertura)
            # Area_flow = Perimetro * x
            # DeltaP = (Q / (Cd * Area_flow))^2
            # F_fluid = DeltaP * Area_port
            
            # Risolviamo analiticamente approssimando Area_flow lineare con la forza
            # Forza Damping Fd ~ v^x
            
            # Modello Ibrido Lineare-Quadratico basato sulla rigidezza
            # Più è rigido, più assomiglia a un orifizio fisso (Quadratico)
            # Più è morbido, più è lineare (Valvola che apre)
            
            # Fattore di smorzamento "base"
            damping_coeff = stiffness_nm * 0.5 
            
            # Forza = coeff * v + idraulica pura
            force = damping_coeff * v + (v**2 * 50) 
            
            forces.append(force)
            
        return pd.DataFrame({"Velocità (m/s)": velocities, "Forza (N)": forces})
