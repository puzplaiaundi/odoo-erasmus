from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestErasmusMovilidad(TransactionCase):
    def setUp(self):
        super().setUp()
        self.persona = self.env["erasmus.persona"].create({
            "tipo_interno": "estudiante",
            "nombre": "Ada",
            "apellido1": "Lovelace",
            "email": "ada.lovelace.movilidad@example.com",
            "movil": "600000001",
            "nif": "12345678A",
        })

    def _minimal_movilidad_vals(self, **overrides):
        vals = {
            "persona_id": self.persona.id,
            "tipo_interno": "estudiante",
            "num_adjuntos_dni": "1",
        }
        vals.update(overrides)
        return vals

    def test_creacion_minima_valida(self):
        movilidad = self.env["erasmus.movilidad"].create(
            self._minimal_movilidad_vals()
        )

        self.assertTrue(movilidad)
        self.assertEqual(movilidad.persona_id, self.persona)
        self.assertEqual(movilidad.tipo_interno, "estudiante")
        self.assertEqual(movilidad.num_adjuntos_dni, "1")
        self.assertEqual(movilidad.estado_datos, "borrador")

    def test_error_si_falta_persona_id(self):
        with self.assertRaises(ValidationError):
            self.env["erasmus.movilidad"].create(
                self._minimal_movilidad_vals(persona_id=False)
            )

    def test_error_si_falta_tipo_interno(self):
        with self.assertRaises(ValidationError):
            self.env["erasmus.movilidad"].with_context(
                default_tipo_interno=False
            ).create({
                "persona_id": self.persona.id,
                "num_adjuntos_dni": "1",
            })

    def test_error_si_falta_num_adjuntos_dni(self):
        with self.assertRaises(ValidationError):
            self.env["erasmus.movilidad"].create(
                self._minimal_movilidad_vals(num_adjuntos_dni=False)
            )

    def test_movilidad_aparece_en_persona_movilidad_ids(self):
        movilidad = self.env["erasmus.movilidad"].create(
            self._minimal_movilidad_vals()
        )

        self.assertIn(movilidad, self.persona.movilidad_ids)
        self.assertEqual(self.persona.movilidad_ids, movilidad)
