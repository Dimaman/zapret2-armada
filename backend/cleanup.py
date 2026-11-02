"""Fixed ExecStopPost entry point; refuses foreign table collisions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.nftables_manager import NftablesManager

if __name__ == "__main__":
    NftablesManager().remove()
