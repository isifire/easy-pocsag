import unittest
import sys
import numpy as np
from native_tx import iq_chunks, SAMPLE_RATE, DEVIATION
from pocsag_generator import PocsagSender, SYNC_CODEWORD

class NativeTests(unittest.TestCase):
    def test_rates_and_phase(self):
        for rate in (512, 1200, 2400):
            raw = b"".join(iq_chunks([1, -1], rate, chunk_size=137))
            iq = np.frombuffer(raw, dtype=np.int8).reshape(-1, 2)
            self.assertEqual(len(iq), 2 * SAMPLE_RATE // rate)
            z = iq[:, 0].astype(float) + 1j * iq[:, 1]
            frequency = np.angle(z[1:] * np.conj(z[:-1])) * SAMPLE_RATE / (2*np.pi)
            split = SAMPLE_RATE // rate
            self.assertAlmostEqual(float(np.mean(frequency[:split-1])), -DEVIATION, delta=10)
            self.assertAlmostEqual(float(np.mean(frequency[split:])), DEVIATION, delta=10)
    def test_chunks_do_not_change_signal(self):
        self.assertEqual(b"".join(iq_chunks([1,-1,0,1],2400,137)), b"".join(iq_chunks([1,-1,0,1],2400,10000)))
    def test_frames_and_no_radio_import(self):
        for mode, text in [('alpha','Hello'),('numeric','123'),('tone','')]:
            batches, words = PocsagSender._create_pocsag_message(1107305,0,text,mode)
            self.assertEqual(words[18], SYNC_CODEWORD)
            self.assertEqual(len(words),18+17*batches)
        self.assertNotIn('gnuradio',sys.modules)
        self.assertNotIn('osmosdr',sys.modules)

if __name__ == '__main__': unittest.main()
