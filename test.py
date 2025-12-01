import matplotlib.pyplot as plt
import matplotlib

# Use Bravura if installed
matplotlib.rcParams["font.family"] = "Bravura"

plt.text(0.5, 0.5, "\U0001D11E", fontsize=80)  # G clef (𝄞)
plt.text(0.5, 0.2, "\U0001D122", fontsize=80)  # F clef (𝄢)
plt.show()