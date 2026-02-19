
import sys
import os

# Ensure the current directory is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cantares.ui.app import CantaresApp

if __name__ == "__main__":
    app = CantaresApp()
    app.run()
