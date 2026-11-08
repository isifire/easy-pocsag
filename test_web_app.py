import json
from pathlib import Path
import threading
import unittest
import urllib.request
import urllib.error
from dataclasses import asdict
import config
from web_app import Controller, Handler, TOKEN, ThreadingHTTPServer, transmission_config
from pocsag_sender import sanitize_text

class WebTests(unittest.TestCase):
    def test_configuration_validation(self):
        data = asdict(config.TransmissionConfig(text="Prueba"))
        self.assertEqual(transmission_config(data).ric, 1107305)
        for field, value in (("ric",0),("bitrate",123),("freq_mhz",float("nan")),("repeat",0),("if_gain",48)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                transmission_config({**data,field:value})

    def test_multiline_message_keeps_word_boundaries(self):
        self.assertEqual(sanitize_text("Hola\nMundo", "alpha"), "Hola Mundo ")

    def test_local_server_protects_transmission_endpoints(self):
        server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
        server.controller = Controller()
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urllib.request.urlopen(base + "/") as response:
                self.assertIn(TOKEN, response.read().decode())
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(urllib.request.Request(base+"/api/send",data=b"{}"))
            self.assertEqual(error.exception.code,403)
            request = urllib.request.Request(base+"/api/state",headers={"X-POCSAG-Token":TOKEN})
            with urllib.request.urlopen(request) as response:
                self.assertEqual(json.load(response)["phase"],"idle")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

if __name__ == '__main__': unittest.main()
