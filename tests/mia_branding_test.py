"""UI-only identity contract: paths/IDs/history must not be mass-renamed."""
import unittest,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Branding(unittest.TestCase):
 def test_observable_not_demo_workflow(self):
  chat=(ROOT/'chat/chat.js').read_text()
  self.assertTrue('Memoria y herramientas: no instrumentado' in chat,'observable disclosure missing')
  self.assertTrue('MIA, acrónimo de MicrotechAI' in chat,'exact acronym disclosure missing')
  self.assertTrue('Modelo · texto recibido por stream' in chat,'SSE delta must be observed separately')
  self.assertNotIn('demo-piper.wav',chat)

 def test_identity(self):
  index=(ROOT/'index.html').read_text();login=(ROOT/'login.html').read_text()
  self.assertIn('<title>Microtech AI',index)
  self.assertNotRegex(index,r'CARGANDO JARVIS|label:\s*\x27JARVIS|MicroTech AI')
  self.assertNotRegex(login,r'(?i)>[^<]*jarvis|<title>[^<]*jarvis')
  self.assertIn("id:'pr-jarvis'",index)
  self.assertIn('MIA',(ROOT/'api/chat.php').read_text())
if __name__=='__main__':unittest.main(verbosity=2)
