import numpy as np
def clip_action(a): return np.clip(a, -1.0, 1.0)
