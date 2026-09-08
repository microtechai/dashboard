"""TTS stdin with real PHP/auth/CSRF and a labeled Piper fixture, not audio quality."""
import unittest
from chat_backend_test import Backend, RUN
class EmojiBackend(Backend):
 def test_tts_stdin_strips_emoji_without_touching_history(self):
  original=self.piper.read_text()
  self.piper.write_text(original.replace('text=sys.stdin.read().strip()', 'text=sys.stdin.read().strip()\nopen('+repr(str(RUN/'spoken.txt'))+',"w").write(text)'))
  try:
   self.login()
   text='Hola 👩🏽‍💻 🇪🇸 🏳️‍🌈 1️⃣ #️⃣ *️⃣ ❤️ ☀︎ 🫠 3.14 € $ £ ¥ −5% π × ÷ ± ∑ ∞ ≤ ≥ = + 42 C++'
   self.assertEqual(self.req('message',{'text':text})[0],200)
   self.assertEqual(self.req()[2]['history'][0]['content'],text)
   self.assertEqual(self.req('tts',{'text':text})[0],200)
   self.assertEqual((RUN/'spoken.txt').read_text(),'Hola 3.14 € $ £ ¥ −5% π × ÷ ± ∑ ∞ ≤ ≥ = + 42 C++')
   self.assertEqual(self.req('tts',{'text':'👩🏽‍💻🇪🇸1️⃣'})[0],400)
  finally:self.piper.write_text(original)
if __name__=='__main__':unittest.main(verbosity=2)
