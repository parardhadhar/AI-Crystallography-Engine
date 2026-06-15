import numpy as np

def calculate_dot_product(g_vector, b_vector):
    """Calculates the g.b dot product."""
    return np.dot(g_vector, b_vector)

def solve_burgers_vector(vanished_g_vectors):
    """
    Given a list of g-vectors where a loop was observed to vanish,
    this function mathematically solves for the possible Burgers vectors (b)
    using the invisibility criterion: g . b = 0.
    """
    print(f"Solving g.b=0 for extinction conditions: {vanished_g_vectors}")
    
    # Standard BCC/FCC dislocation Burgers vectors to test against
    possible_b_vectors = {
        "1/2[111]": np.array([0.5, 0.5, 0.5]),
        "1/2[-111]": np.array([-0.5, 0.5, 0.5]),
        "1/2[1-11]": np.array([0.5, -0.5, 0.5]),
        "1/2[11-1]": np.array([0.5, 0.5, -0.5]),
        "[100]": np.array([1, 0, 0]),
        "[010]": np.array([0, 1, 0]),
        "[001]": np.array([0, 0, 1]),
        "1/2[110]": np.array([0.5, 0.5, 0]),
        "1/2[1-10]": np.array([0.5, -0.5, 0]),
        "1/2[101]": np.array([0.5, 0, 0.5]),
        "1/2[011]": np.array([0, 0.5, 0.5]),
        "1/3[111]": np.array([1/3, 1/3, 1/3])
    }
    
    valid_burgers = []
    
    for name, b in possible_b_vectors.items():
        is_valid = True
        for g in vanished_g_vectors:
            # g.b = 0 means the loop is invisible
            if abs(calculate_dot_product(g, b)) > 1e-5:
                is_valid = False
                break
        
        if is_valid:
            valid_burgers.append(name)
            
    if not valid_burgers:
        return "Unknown (Mixed/Residual Contrast)"
        
    return " or ".join(valid_burgers)

if __name__ == "__main__":
    # Test case from the journal image:
    # Loop is missing in g=(020) and g=(-220)
    g_020 = np.array([0, 2, 0])
    g_m220 = np.array([-2, 2, 0])
    
    result = solve_burgers_vector([g_020, g_m220])
    print(f"Mathematically solved Burgers vector: {result}")
