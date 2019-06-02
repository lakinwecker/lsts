"""
lsts is a simple socket proxy which proxies a server to a given set of clients.

But it does not send the data immediately, every piece of data that it receives
is delayed by some time set on the commane line.

It is intended to similuate timeouts and delays in responses to a server so that
you can easily test your timeout and other facilities for dealing with this
situation.
"""

import asyncio
import click
import sys
import time
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass

@dataclass
class Address:
    '''Class for keeping track of an host/socket'''
    host: str
    port: int

@dataclass
class ReaderWriter:
    '''Class for keeping track of a reader/writer pair'''
    reader: StreamReader
    writer: StreamWriter

async def proxy_reads(reader: StreamReader, writer: StreamWriter, delay: float):
    print(f"Proxy_reads ")
    while True:
        data = await reader.read(100)
        await asyncio.sleep(delay)
        writer.write(data)

async def proxy_connection(client: ReaderWriter, server: Address, delay: float):
    addr = client.writer.get_extra_info('peername')
    print(f"Connection from {addr!r}")
    r, w = await asyncio.open_connection(server.host, server.port)
    print(f"Connected to server")
    server = ReaderWriter(r, w)

    read_task = asyncio.create_task(proxy_reads(client.reader, server.writer, delay))
    write_task = asyncio.create_task(proxy_reads(server.reader, client.writer, 0))
    await read_task
    await write_task

async def connect_to_server_and_listen(
    server: Address, listen: Address, delay: float
):

    tasks = []
    def handle_connect(r, w):
        client = ReaderWriter(r, w)
        tasks.append(asyncio.create_task(proxy_connection(client, server, delay)))

    listen_server = await asyncio.start_server(handle_connect, listen.host, listen.port)
    addr = listen_server.sockets[0].getsockname()
    print(f'Listening on {addr}')

    async with listen_server:
        await listen_server.serve_forever()
    for task in tasks:
        await task

@click.command()
@click.option('--server-host', required=True, help='IP of the server to proxy')
@click.option('--server-port', required=True, type=click.INT, help='Port of the server to proxy')
@click.option('--listen-host', required=True, help='IP of the server to proxy')
@click.option('--listen-port', required=True, type=click.INT, help='Port on which to listen')
@click.option('--delay', required=True, type=click.FLOAT, help='Delay in seconds to wait before sending data (floating point)')
def proxy(server_host, server_port, listen_host, listen_port, delay):
    """Proxies data received on listen (host:port) to server (host:port) after a delay"""
    asyncio.run(connect_to_server_and_listen(
        Address(server_host, server_port),
        Address(listen_host, listen_port),
        delay
    ))

if __name__ == '__main__':
    proxy()
