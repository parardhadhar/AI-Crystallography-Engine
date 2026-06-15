import numpy as np

def _get_image_basis(za: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    za = za / (np.linalg.norm(za) + 1e-12)
    
    preferred_x = [
        np.array([1, 0, 0], dtype=float),
        np.array([1, -1, 0], dtype=float),
        np.array([0, 1, 0], dtype=float)
    ]
    
    e_x = None
    for p_x in preferred_x:
        proj = p_x - np.dot(p_x, za) * za
        norm = np.linalg.norm(proj)
        if norm > 1e-3:
            e_x = proj / norm
            break
            
    # e_y = Z x X. If Z is OUT and X is RIGHT, Z x X points UP.
    # We want standard Image Y (DOWN), so we negate it: e_y = X x Z
    e_y = np.cross(e_x, za)
    e_y = e_y / (np.linalg.norm(e_y) + 1e-12)
    
    return e_x, e_y

def theoretical_g_angle(g, za):
    e_x, e_y = _get_image_basis(za)
    x_comp = np.dot(g, e_x)
    y_comp = np.dot(g, e_y)
    return np.degrees(np.arctan2(y_comp, x_comp))

za = np.array([0,1,1])
g = np.array([1,1,-1])
print("Angle of [1,1,-1] on [011]:", theoretical_g_angle(g, za))

za = np.array([0,0,1])
g = np.array([2,0,0])
print("Angle of [2,0,0] on [001]:", theoretical_g_angle(g, za))
g = np.array([0,2,0])
print("Angle of [0,2,0] on [001]:", theoretical_g_angle(g, za))
