"""
pytest conftest — adiciona scripts/ ao sys.path para importação nos testes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
