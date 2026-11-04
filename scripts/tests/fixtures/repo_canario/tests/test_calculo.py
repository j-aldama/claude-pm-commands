import unittest

from app.calculo import promedio, total


class TotalTest(unittest.TestCase):
    def test_suma_con_descuento(self):
        self.assertEqual(total([10, 10], 0.5), 10.0)

    def test_descuento_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            total([10], 1.5)


class PromedioTest(unittest.TestCase):
    def test_promedio(self):
        self.assertEqual(promedio([2, 4]), 3)

    def test_lista_vacia_es_error(self):
        with self.assertRaises(ValueError):
            promedio([])
