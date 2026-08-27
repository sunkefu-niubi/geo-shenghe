#!/usr/bin/env python3
"""门店展示页本地预览服务器。支持 --port / --host 参数转发。"""
import argparse
import functools
import http.server
import socketserver

parser = argparse.ArgumentParser()
parser.add_argument("port_positional", nargs="?", type=int, default=None)
parser.add_argument("--port", "-p", type=int, default=None)
parser.add_argument("--host", "-b", default="127.0.0.1")
args = parser.parse_args()

port = args.port or args.port_positional or 7100
handler = functools.partial(http.server.SimpleHTTPRequestHandler)

with socketserver.TCPServer((args.host, port), handler) as httpd:
    print(f"门店展示页预览: http://{args.host}:{port}/")
    httpd.serve_forever()
