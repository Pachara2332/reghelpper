# -*- coding: utf-8 -*-
"""
เซิร์ฟเวอร์ Demo สำหรับทดสอบระบบลงทะเบียน MSU
รันที่ http://localhost:8899
"""

import http.server
import socketserver
import os

PORT = 8899
DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIR)

Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(('', PORT), Handler) as httpd:
    print(f'Demo server running at http://localhost:{PORT}')
    httpd.serve_forever()
