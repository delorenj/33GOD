import io
import unittest
from unittest.mock import patch
import uuid

import server


def event():
    return {"id": str(uuid.uuid4()), "source": "urn:33god:aperture:g2", "specversion": "1.0",
            "type": server.SUBJECT, "subject": server.SUBJECT,
            "time": "2026-10-23T18:00:00Z", "datacontenttype": "application/json", "data": {"ping": True}}


class Connection:
    def __init__(self, response):
        self.response = io.BytesIO(response)
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def settimeout(self, value):
        pass

    def makefile(self, mode):
        return self.response

    def sendall(self, data):
        self.sent.append(data)


class Tests(unittest.TestCase):
    def test_valid_cloud_event(self):
        server.validate(event())

    def test_no_other_subjects(self):
        for field in ["subject", "type", "source", "specversion", "datacontenttype"]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                value = event()
                value[field] = "not-allowed"
                server.validate(value)

    def test_required_fields(self):
        for field in ["id", "time", "data"]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                value = event()
                del value[field]
                server.validate(value)

    def test_bad_uuid_time_data(self):
        for field, data in [("id", "invalid"), ("time", "invalid"), ("data", [])]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                value = event()
                value[field] = data
                server.validate(value)

    def test_nats_ping_and_ack(self):
        body = b'{"stream":"G2_SMOKE","seq":7}'
        conn = Connection(b'INFO {}\r\nPING\r\nMSG x 1 ' + str(len(body)).encode() + b'\r\n' + body + b'\r\n')
        with patch("server.socket.create_connection", return_value=conn):
            result = server.request(server.SUBJECT, {"ping": True})
        self.assertEqual(result, {"stream": "G2_SMOKE", "seq": 7})
        self.assertIn(b"PONG\r\n", conn.sent)
        self.assertTrue(any(x.startswith(b"PUB " + server.SUBJECT.encode()) for x in conn.sent))

    def test_jetstream_error_propagates(self):
        body = b'{"error":{"err_code":10059}}'
        conn = Connection(b'INFO {}\r\nMSG x 1 ' + str(len(body)).encode() + b'\r\n' + body + b'\r\n')
        with patch("server.socket.create_connection", return_value=conn), self.assertRaises(RuntimeError):
            server.request(server.SUBJECT, {})

    def test_disconnect_does_not_ack(self):
        conn = Connection(b'INFO {}\r\n')
        with patch("server.socket.create_connection", return_value=conn), self.assertRaises(RuntimeError):
            server.request(server.SUBJECT, {})

    def test_truncated_message_does_not_ack(self):
        conn = Connection(b'INFO {}\r\nMSG x 1 20\r\n{}\r\n')
        with patch("server.socket.create_connection", return_value=conn), self.assertRaises(RuntimeError):
            server.request(server.SUBJECT, {})


if __name__ == "__main__":
    unittest.main()
