"""Pruebas de la rúbrica de planes (D4)."""
import json
import os
import unittest
from pathlib import Path

RAIZ = Path(os.environ.get("CLAUDE_HOME") or Path.home() / ".claude")


class RubricaTest(unittest.TestCase):
    def setUp(self):
        self.criterios = json.loads((RAIZ / "rubricas" / "plan.json").read_text())["criterios"]

    def test_cada_criterio_trae_sus_campos(self):
        for c in self.criterios:
            with self.subTest(c.get("id")):
                self.assertTrue(c["exige"].strip())
                self.assertTrue(c["como_se_verifica"].strip())
                self.assertIsInstance(c["obligatorio"], bool)

    def test_ids_c1_a_c9_sin_repetir(self):
        ids = [c["id"] for c in self.criterios]
        self.assertEqual(ids, [f"C{i}" for i in range(1, 10)])

    def test_c9_diseno_es_obligatorio(self):
        c9 = next(c for c in self.criterios if c["id"] == "C9")
        self.assertTrue(c9["obligatorio"])
        self.assertIn("contradicciones", c9["exige"])


if __name__ == "__main__":
    unittest.main()
